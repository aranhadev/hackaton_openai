#!/usr/bin/env python3
"""Command-line interface for the local Rank 02 practice exam."""

import getpass
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# sshd starts ForceCommand with a restricted environment and may drop PYTHONPATH.
# Resolve this entry point through the symlink so the package remains importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from examshell.profiles import ExamMode, UserProfile, get_exam_mode, get_user_profile
from examshell.grading import (
    REPOSITORY,
    GradeError,
    ensure_user_repository,
    grade,
    git_url_for_user,
    latest_commit,
    publish_next_subject,
    repository_for_user,
)
from examshell.state import load_state, save_state
from examshell.catalog import by_slug
from examshell.trilha import (
    ActivityNoLongerActive,
    AuthenticationError,
    NoActivePath,
    TrilhaAPIError,
    TrilhaClient,
)


WELCOME = Path(__file__).with_name("ssh-README.md")
ACTIVE_PROFILE: UserProfile | None = None
TRILHA_API_URL = os.environ.get("TRILHA_API_URL", "").strip().rstrip("/")
TRILHA_API_SOURCE = os.environ.get("TRILHA_SOURCE", "examshell")
try:
    TRILHA_API_TIMEOUT = float(os.environ.get("TRILHA_API_TIMEOUT", "10"))
except ValueError:
    TRILHA_API_TIMEOUT = 10
TRILHA_CLIENT: TrilhaClient | None = None
TRILHA_STEP: dict | None = None
TRILHA_NO_PATH = False
TRILHA_REPO_KEY: str | None = None


def _active_mode() -> ExamMode:
    if ACTIVE_PROFILE is None:
        raise RuntimeError("Faça login antes de usar os comandos do ExamShell.")
    return get_exam_mode(ACTIVE_PROFILE.mode)


def _active_state() -> dict | None:
    if ACTIVE_PROFILE is None:
        return None
    return load_state(ACTIVE_PROFILE.login)


def _active_git_url(*, public: bool = False) -> str:
    if ACTIVE_PROFILE is None:
        raise RuntimeError("Faça login antes de consultar o repositório Git.")
    return git_url_for_user(ACTIVE_PROFILE.login, public=public)


def _trilha_repo_key() -> str:
    if TRILHA_CLIENT is None or TRILHA_CLIENT.identity is None:
        raise RuntimeError("Faça login no app antes de acessar o repositório da trilha.")
    identity = "".join(character for character in str(TRILHA_CLIENT.identity) if character.isalnum())
    if not identity:
        raise RuntimeError("O app retornou um identity inválido.")
    return f"trilha-{identity}"


def _trilha_git_url(*, public: bool = False) -> str:
    if TRILHA_REPO_KEY is None:
        raise RuntimeError("O repositório da trilha ainda não foi inicializado.")
    return git_url_for_user(TRILHA_REPO_KEY, public=public)


def _connect_trilha() -> bool:
    global TRILHA_CLIENT
    client = TrilhaClient(TRILHA_API_URL, TRILHA_API_TIMEOUT, TRILHA_API_SOURCE)
    while True:
        try:
            username = input("Usuário do app: ").strip()
            if not username:
                print("Informe o usuário do app.")
                continue
            password = getpass.getpass("Senha do app: ")
            identity = client.login(username, password)
            TRILHA_CLIENT = client
            print(f"Login no app realizado. Aluno ID: {identity}.")
            return True
        except EOFError:
            print("\nLogin cancelado.")
            return False
        except AuthenticationError:
            print("Usuário ou senha inválidos. Tente novamente.")
        except TrilhaAPIError as error:
            print(f"Não consegui conectar ao app: {error}")
            return False


def _show_trilha_step(step: dict, exercise=None) -> None:
    position = step.get("position", "?")
    total = step.get("total", "?")
    skill = step.get("skill_title") or "Trilha personalizada"
    print(f"\nPasso {position} de {total} · {skill}")
    if step.get("title"):
        print(step["title"])
    if step.get("reason"):
        print(f"Motivo: {step['reason']}")
    if step.get("status") in {"pending", "failed"}:
        print(f"Status: {step['status']} · tentativa {step.get('attempts', 0) + 1}")
    if exercise is None:
        print(f"Sua próxima atividade ({step.get('title', 'atividade')}) é no site: {TRILHA_API_URL}/trilha")
        print("grademe fica indisponível até a trilha indicar um exercício do ExamShell.")
        return
    print(f"Exercício: {exercise.slug} (Level {exercise.level})")
    print(exercise.description)
    print(f"Enunciado: subjects/subject/{exercise.slug}/subject.en.md")
    print(f"Arquivo a enviar: rendu/{exercise.slug}/{exercise.source}")
    print(f"Repositório Git: {_trilha_git_url(public=True)}")
    print("Clone/edite/envie o repositório no terminal normal da sua máquina; volte aqui para executar grademe.")


def _refresh_trilha_step(*, announce: bool = True) -> dict | None:
    global TRILHA_STEP, TRILHA_NO_PATH, TRILHA_REPO_KEY
    if TRILHA_CLIENT is None:
        if not _connect_trilha():
            return None
    try:
        step = TRILHA_CLIENT.next_step()
    except NoActivePath:
        TRILHA_STEP = None
        TRILHA_NO_PATH = True
        if announce:
            print(f"Nenhuma trilha ativa. Faça o diagnóstico em {TRILHA_API_URL}/diagnostico.")
        return None

    TRILHA_NO_PATH = False
    TRILHA_STEP = step
    if step.get("finished"):
        if announce:
            print("Parabéns! Sua trilha foi concluída. Execute finish para encerrar.")
        return step

    slug = step.get("examshell_id")
    if not slug:
        if announce:
            _show_trilha_step(step)
        return step
    try:
        exercise = by_slug(str(slug))
    except KeyError:
        if announce:
            print(f"O exercício {slug} ainda não está disponível neste ExamShell. Continue pelo site: {TRILHA_API_URL}/trilha")
        return step

    TRILHA_REPO_KEY = _trilha_repo_key()
    repository = ensure_user_repository(
        TRILHA_REPO_KEY,
        first_subject=exercise.slug,
        subject_prefix="subjects/subject",
    )
    head = latest_commit(repository)
    if head is None:
        raise RuntimeError("O repositório Git da trilha não tem um commit inicial.")

    state = load_state(TRILHA_REPO_KEY)
    step_changed = state is None or state.get("activity_id") != step.get("activity_id") or state.get("examshell_id") != slug
    if state is None:
        state = {
            "username": TRILHA_REPO_KEY,
            "mode": "api",
            "identity": TRILHA_CLIENT.identity,
            "activity_id": step.get("activity_id"),
            "examshell_id": slug,
            "graded_commit": head,
            "attempts": [],
        }
    elif step_changed:
        state["activity_id"] = step.get("activity_id")
        state["examshell_id"] = slug
        state["graded_commit"] = head
        state["attempts"] = []

    subject_path = f"subjects/subject/{exercise.slug}/subject.en.md"
    subject = _git(
        "git", f"--git-dir={repository}", "ls-tree", "-r", "--name-only", "refs/heads/master", "--", subject_path,
        check=False,
    ).stdout.strip()
    if not subject:
        published = publish_next_subject(
            exercise.slug,
            _trilha_git_url(),
            repository,
            subject_prefix="subjects/subject",
        )
        if step_changed:
            state["graded_commit"] = published
        head = published
    state["identity"] = TRILHA_CLIENT.identity
    save_state(state)

    if announce:
        _show_trilha_step(step, exercise)
    return step


def _trilha_status() -> int:
    if TRILHA_CLIENT is None and not _connect_trilha():
        return 1
    try:
        step = _refresh_trilha_step()
        if step is not None and not step.get("finished"):
            if step.get("examshell_id"):
                state = load_state(TRILHA_REPO_KEY or _trilha_repo_key())
                if state is not None:
                    print(f"Aluno ID: {TRILHA_CLIENT.identity} · tentativas nesta atividade: {step.get('attempts', 0)}")
            elif step.get("title"):
                print(f"Atividade do site: {step['title']}")
        return 0
    except (TrilhaAPIError, GradeError, RuntimeError) as error:
        print(f"Não consegui consultar a trilha: {error}")
        return 1


def _login() -> bool:
    global ACTIVE_PROFILE
    while ACTIVE_PROFILE is None:
        try:
            login = input("Login (trial/normal): ").strip()
        except EOFError:
            print("\nLogin cancelado.")
            return False
        profile = get_user_profile(login)
        if profile is None:
            print("Login desconhecido. Use trial ou normal.")
            continue
        ACTIVE_PROFILE = profile
    print(f"Login: {ACTIVE_PROFILE.login} — modo {ACTIVE_PROFILE.mode}.")
    return True


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Falha ao consultar o repositório Git.")
    return result


def _commit_exists(repository: Path, commit: str | None) -> bool:
    if not commit:
        return False
    return _git(
        "git", f"--git-dir={repository}", "cat-file", "-e", f"{commit}^{{commit}}", check=False
    ).returncode == 0


def _show_exercise(index: int, exercises: tuple) -> None:
    exercise = exercises[index]
    print(f"\nQuestão {index + 1}/{len(exercises)} — {exercise.slug} (Level {exercise.level})")
    print(exercise.description)
    print(f"\nEnunciado: subjects/{exercise.slug}/subject.en.md")
    print(f"Arquivo a enviar: rendu/{exercise.slug}/{exercise.source}")
    print(f"Repositório Git: {_active_git_url(public=True)}")
    print("No terminal normal da sua máquina, clone/edite/envie o repositório; volte a esta conexão SSH para executar grademe.")
    print("Faça git add, git commit e git push antes de executar grademe.")
    if index > 0:
        print("Após a publicação do novo enunciado, atualize seu clone com: git pull --rebase")
    print()


def _start_exam() -> int:
    if WELCOME.is_file():
        print(WELCOME.read_text(encoding="utf-8"))
    if TRILHA_API_URL:
        if not _connect_trilha():
            return 0
        try:
            _refresh_trilha_step()
        except (TrilhaAPIError, GradeError, RuntimeError) as error:
            print(f"Não consegui carregar a próxima atividade: {error}")
        return 0
    if not _login():
        return 1
    if not REPOSITORY.is_dir():
        raise RuntimeError("O repositório do exame ainda não foi inicializado.")
    user_repository = ensure_user_repository(ACTIVE_PROFILE.login)
    head = latest_commit(user_repository)
    if head is None:
        raise RuntimeError("O repositório do exame não tem um commit inicial.")
    mode = _active_mode()
    state = load_state(ACTIVE_PROFILE.login, migrate_legacy=ACTIVE_PROFILE.login == "trial")
    if state is None or state.get("finished"):
        state = {
            "username": ACTIVE_PROFILE.login,
            "mode": mode.name,
            "index": 0,
            "graded_commit": head,
            "finished": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "attempts": [],
        }
        save_state(state)
        print(f"ExamShell Rank 02 ({mode.name}) iniciado. Boa prova!")
    elif not _commit_exists(user_repository, state.get("graded_commit")):
        state["graded_commit"] = head
        save_state(state)
    _ensure_results(state, mode.exercises)
    if state["index"] >= len(mode.exercises):
        correct = sum(result["passed"] for result in state["results"])
        print(f"Exame concluído: {correct}/{len(mode.exercises)} questões corretas. Execute finish para encerrar.")
        return 0
    _show_exercise(state["index"], mode.exercises)
    return 0


def examshell() -> int:
    if _start_exam() != 0:
        return 1
    print("Digite grademe para avaliar, status para ver o progresso, finish para encerrar ou exit para sair do ExamShell.")
    while True:
        try:
            command = input("examshell> ").strip()
        except EOFError:
            print("\nSaindo do ExamShell. A sessão continua salva; reconecte por SSH para retornar.")
            return 0
        if command == "grademe":
            grademe()
        elif command == "status":
            status()
        elif command == "finish":
            finish()
            return 0
        elif command in {"exit", "quit"}:
            print("Saindo do ExamShell. A sessão continua salva; reconecte por SSH para retornar.")
            return 0
        elif command in {"help", "?"}:
            print("Comandos: grademe, status, finish, help, exit")
        elif command:
            print(f"Comando desconhecido: {command}. Digite help para ver os comandos disponíveis.")


def _confirm_grade() -> bool:
    try:
        answer = input("Verify that you made git push. Do you want to continue? [Y/N] ").strip()
    except EOFError:
        print("\nAvaliação cancelada.")
        return False
    if answer in {"Y", "y"}:
        return True
    print("Avaliação cancelada. Nenhum teste foi executado.")
    return False


def _ensure_results(state: dict, exercises: tuple) -> None:
    """Backfill sessions created before per-question outcomes were recorded."""
    if "results" not in state:
        state["results"] = [
            {"slug": exercises[index].slug, "passed": True, "commit": None, "feedback": "Aprovada em sessão anterior."}
            for index in range(min(state.get("index", 0), len(exercises)))
        ]
        state.setdefault("attempts", [])
        state.setdefault("mode", ACTIVE_PROFILE.mode if ACTIVE_PROFILE else "trial")
        save_state(state)


def grademe() -> int:
    if TRILHA_API_URL:
        return _trilha_grademe()
    if not _confirm_grade():
        return 0
    state = _active_state()
    if state is None or state.get("finished"):
        print("Nenhum exame ativo. Execute examshell primeiro.")
        return 1
    mode = _active_mode()
    exercises = mode.exercises
    if state["index"] >= len(exercises):
        print("Exame concluído. Execute finish para encerrar.")
        return 0
    _ensure_results(state, exercises)

    commit = latest_commit(repository_for_user(ACTIVE_PROFILE.login))
    if commit is None:
        print("Ainda não há commit enviado. Faça git commit e git push antes de executar grademe.")
        return 1
    if commit == state.get("graded_commit"):
        print("Não encontrei um push novo desde a última avaliação. Envie sua solução com git push.")
        return 1

    exercise = exercises[state["index"]]
    required_path = f"rendu/{exercise.slug}/{exercise.source}"
    changed = _git(
        "git", f"--git-dir={repository_for_user(ACTIVE_PROFILE.login)}", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit
    ).stdout.splitlines()
    if required_path not in changed:
        print(f"O último commit enviado não contém {required_path}.")
        print("Adicione o arquivo da questão, faça commit e push; a questão continua aberta.")
        return 1

    print(f"Clonando o repositório e avaliando {exercise.slug} no commit {commit[:8]}...")
    try:
        passed, feedback = grade(commit, exercise, _active_git_url())
    except GradeError as error:
        print(f"Não foi possível concluir a avaliação: {error}")
        return 1
    print(feedback)

    next_index = state["index"] + 1
    result_record = {
        "slug": exercise.slug,
        "passed": passed,
        "commit": commit,
        "feedback": feedback,
        "graded_at": datetime.now(timezone.utc).isoformat(),
    }
    attempt_record = dict(result_record)
    state.setdefault("attempts", []).append(attempt_record)
    if not passed and not mode.advance_on_failure:
        state["graded_commit"] = commit
        save_state(state)
        print("Questão não aprovada. O modo normal mantém a questão atual; corrija a solução, faça outro commit e push, e tente novamente.")
        return 0

    if next_index < len(exercises):
        next_slug = exercises[next_index].slug
        try:
            published_commit = publish_next_subject(
                next_slug, _active_git_url(), repository_for_user(ACTIVE_PROFILE.login)
            )
        except GradeError as error:
            outcome = "correta" if passed else "incorreta"
            print(f"Solução avaliada como {outcome}, mas não consegui publicar o próximo subject: {error}")
            print("Execute grademe novamente para concluir a avaliação e avançar.")
            return 1
        state["graded_commit"] = published_commit
        state["index"] = next_index
        state["results"].append(result_record)
        save_state(state)
        if passed:
            print(f"Questão marcada como correta. O subject {next_slug} foi enviado ao repositório Git.")
        else:
            print(f"Questão marcada como errada no modo trial. O subject {next_slug} foi enviado ao repositório Git.")
        _show_exercise(next_index, exercises)
        return 0

    state["graded_commit"] = commit
    state["index"] = next_index
    state["results"].append(result_record)
    save_state(state)
    correct = sum(result["passed"] for result in state["results"])
    print(f"Exame concluído: {correct}/{len(exercises)} questões corretas. Execute finish para encerrar.")
    return 0


def _trilha_grademe() -> int:
    if not _confirm_grade():
        return 0
    if TRILHA_CLIENT is None and not _connect_trilha():
        return 1
    try:
        step = TRILHA_STEP or _refresh_trilha_step()
        if step is None or step.get("finished") or TRILHA_NO_PATH:
            print("Não há uma atividade do ExamShell disponível para avaliar agora.")
            return 1
        slug = step.get("examshell_id")
        if not slug:
            print("A próxima atividade deve ser concluída no site; grademe está indisponível.")
            return 1
        try:
            exercise = by_slug(str(slug))
        except KeyError:
            print(f"O exercício {slug} ainda não está disponível neste ExamShell.")
            return 1

        repo_key = _trilha_repo_key()
        repository = repository_for_user(repo_key)
        state = load_state(repo_key)
        if state is None:
            _refresh_trilha_step(announce=False)
            state = load_state(repo_key)
        if state is None:
            print("Não consegui inicializar o estado da atividade. Execute status e tente novamente.")
            return 1

        commit = latest_commit(repository)
        if commit is None:
            print("Ainda não há commit enviado. Faça git commit e git push antes de executar grademe.")
            return 1
        if commit == state.get("graded_commit"):
            print("Não encontrei um push novo desde a última avaliação. Envie sua solução com git push.")
            return 1

        required_path = f"rendu/{exercise.slug}/{exercise.source}"
        changed = _git(
            "git", f"--git-dir={repository}", "diff-tree", "--root", "--no-commit-id",
            "--name-only", "-r", commit,
        ).stdout.splitlines()
        if required_path not in changed:
            print(f"O último commit enviado não contém {required_path}.")
            print("Adicione ou altere o arquivo da questão, faça commit e push; a questão continua aberta.")
            return 1

        print(f"Clonando o repositório e avaliando {exercise.slug} no commit {commit[:8]}...")
        passed, feedback = grade(commit, exercise, _trilha_git_url())
        print(feedback)
        try:
            TRILHA_CLIENT.complete(step["activity_id"], passed)
        except ActivityNoLongerActive:
            print("A atividade mudou no app. Vou carregar a trilha atualizada.")
            _refresh_trilha_step()
            return 0

        state["graded_commit"] = commit
        state.setdefault("attempts", []).append({
            "slug": exercise.slug,
            "activity_id": step.get("activity_id"),
            "passed": passed,
            "commit": commit,
            "graded_at": datetime.now(timezone.utc).isoformat(),
            "feedback": feedback,
        })
        save_state(state)
        print("Resultado registrado na trilha: " + ("correto." if passed else "incorreto."))
        _refresh_trilha_step()
        return 0
    except (TrilhaAPIError, GradeError, RuntimeError, KeyError) as error:
        print(f"Não consegui concluir a avaliação: {error}")
        return 1


def status() -> int:
    if TRILHA_API_URL:
        return _trilha_status()
    state = _active_state()
    if state is None:
        print("Nenhum exame iniciado. Execute examshell.")
    elif state.get("finished"):
        print("Exame encerrado.")
    elif state["index"] >= len(_active_mode().exercises):
        _ensure_results(state, _active_mode().exercises)
        correct, wrong = _score(state)
        print(f"Exame concluído: {correct} corretas, {wrong} erradas de {len(_active_mode().exercises)} questões.")
    else:
        exercises = _active_mode().exercises
        _ensure_results(state, exercises)
        correct, wrong = _score(state)
        print(f"Progresso: {state['index']}/{len(exercises)} avaliadas — {correct} corretas, {wrong} erradas.")
        print(f"Questão atual: {exercises[state['index']].slug}.")
        attempts = [attempt for attempt in state.get("attempts", []) if attempt.get("slug") == exercises[state["index"]].slug]
        if attempts and not _active_mode().advance_on_failure:
            print(f"Tentativas nesta questão: {len(attempts)}.")
    return 0


def _score(state: dict) -> tuple[int, int]:
    results = state.get("results", [])
    correct = sum(bool(result.get("passed")) for result in results)
    return correct, len(results) - correct


def finish() -> int:
    if TRILHA_API_URL:
        if TRILHA_STEP and TRILHA_STEP.get("finished"):
            print("Trilha encerrada. O progresso foi registrado pelo app.")
        else:
            print("Sessão do ExamShell encerrada. O progresso da trilha fica salvo no app.")
        return 0
    state = _active_state()
    if state is None:
        print("Nenhum exame iniciado.")
        return 0
    state["finished"] = True
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    _ensure_results(state, _active_mode().exercises)
    correct, wrong = _score(state)
    print(f"Exame encerrado: {correct} corretas, {wrong} erradas de {len(state.get('results', []))} questões avaliadas.")
    return 0


def main() -> int:
    command = Path(sys.argv[0]).name
    if command == "cli.py":
        command = sys.argv[1] if len(sys.argv) > 1 else "help"
    commands = {"examshell": examshell, "grademe": grademe, "status": status, "finish": finish}
    if command not in commands:
        print("Comandos disponíveis: examshell, grademe, status, finish")
        return 0 if command == "help" else 2
    try:
        return commands[command]()
    except (OSError, RuntimeError, GradeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
