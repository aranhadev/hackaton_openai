"""Grade a user's exam repository and publish that user's next subject."""

import os
import re
import resource
import shutil
import subprocess
import tempfile
from pathlib import Path

from examshell.catalog import Exercise


GIT_ROOT = Path(os.environ.get("EXAMSHELL_GIT_ROOT", "/var/lib/examshell/git"))
REPOSITORY = GIT_ROOT / "exam.git"
SUBJECT_SOURCE_ROOT = Path("/opt/examshell/subjects")
GIT_URL = os.environ.get("EXAMSHELL_GIT_URL", "git://localhost:9418/exam.git")


class GradeError(Exception):
    pass


def latest_commit(repository: Path = REPOSITORY) -> str | None:
    result = subprocess.run(
        ["git", f"--git-dir={repository}", "rev-parse", "--verify", "refs/heads/master"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def repository_for_user(username: str) -> Path:
    safe_username = re.sub(r"[^a-zA-Z0-9_-]", "", username)
    if not safe_username:
        raise GradeError("Nome de usuário inválido para o repositório Git.")
    return GIT_ROOT / f"{safe_username}.git"


def git_url_for_user(username: str, *, public: bool = False) -> str:
    base_url = os.environ.get("EXAMSHELL_PUBLIC_GIT_URL", GIT_URL) if public else GIT_URL
    return base_url.rsplit("/", 1)[0] + f"/{username}.git"


def ensure_user_repository(
    username: str,
    *,
    first_subject: str | None = "ft_strlen",
    subject_prefix: str = "subjects",
) -> Path:
    """Create a separate clean Git repo for a local profile."""
    repository = repository_for_user(username)
    if repository.exists():
        return repository
    first_subject_source = SUBJECT_SOURCE_ROOT / first_subject if first_subject else None
    if first_subject_source is not None and not first_subject_source.is_dir():
        raise GradeError("Não encontrei o subject inicial para preparar o repositório do login.")
    with tempfile.TemporaryDirectory(prefix="examshell-init-") as temp_dir:
        checkout = Path(temp_dir) / "exam"
        initialized = subprocess.run(
            ["git", "init", "--initial-branch=master", str(checkout)],
            capture_output=True,
            text=True,
            check=False,
        )
        if initialized.returncode:
            raise GradeError(initialized.stderr.strip() or "Não consegui inicializar o repositório do login.")
        for key, value in (("user.name", "ExamShell subjects"), ("user.email", "examshell@localhost")):
            configured = subprocess.run(
                ["git", "-C", str(checkout), "config", key, value], capture_output=True, text=True, check=False
            )
            if configured.returncode:
                raise GradeError(configured.stderr.strip() or "Não consegui configurar o repositório do login.")
        (checkout / "subjects").mkdir()
        if first_subject_source is not None:
            subject_destination = checkout / subject_prefix / first_subject
            subject_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(first_subject_source, subject_destination)
        (checkout / "rendu").mkdir()
        (checkout / "rendu" / ".gitkeep").touch()
        added = subprocess.run(
            ["git", "-C", str(checkout), "add", "subjects", "rendu"], capture_output=True, text=True, check=False
        )
        if added.returncode:
            raise GradeError(added.stderr.strip() or "Não consegui preparar os arquivos iniciais do login.")
        committed = subprocess.run(
            ["git", "-C", str(checkout), "commit", "-m", "Initialize exam repository"],
            capture_output=True,
            text=True,
            check=False,
        )
        if committed.returncode:
            raise GradeError(committed.stderr.strip() or "Não consegui criar o commit inicial do login.")
        cloned = subprocess.run(
            ["git", "clone", "--bare", "--branch", "master", str(checkout), str(repository)],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if cloned.returncode:
            shutil.rmtree(repository, ignore_errors=True)
            raise GradeError("Não consegui preparar o repositório Git deste login: " + (cloned.stderr.strip() or "erro Git"))
    for key, value in (
        ("daemon.export", "true"),
        ("daemon.receivepack", "true"),
        ("receive.denyNonFastForwards", "true"),
        ("receive.denyDeletes", "true"),
        ("core.sharedRepository", "group"),
    ):
        configured = subprocess.run(
            ["git", f"--git-dir={repository}", "config", key, value],
            capture_output=True,
            text=True,
            check=False,
        )
        if configured.returncode:
            raise GradeError(configured.stderr.strip() or "Não consegui configurar o repositório do login.")
    for path in (repository, *repository.rglob("*")):
        current_mode = path.stat().st_mode
        if path.is_dir():
            os.chmod(path, current_mode | 0o2775)
        elif path.is_file():
            os.chmod(path, current_mode | 0o0664)
    return repository


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024, 64 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout: float = 4,
    apply_limits: bool = True,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            preexec_fn=_limits if apply_limits else None,
        )
    except subprocess.TimeoutExpired as exc:
        raise GradeError("Tempo limite excedido durante a compilação ou execução.") from exc


def _clone_exam_repo(repository_url: str, destination: Path) -> None:
    result = subprocess.run(
        ["git", "clone", "--branch", "master", "--single-branch", repository_url, str(destination)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise GradeError("Não consegui clonar o repositório do exame: " + (result.stderr.strip() or "erro Git"))


def grade(commit: str, exercise: Exercise, repository_url: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="examshell-grade-") as temp_dir:
        work = Path(temp_dir)
        checkout = work / "exam"
        _clone_exam_repo(repository_url, checkout)
        cloned_commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if cloned_commit != commit:
            raise GradeError("O repositório mudou durante a avaliação. Execute grademe novamente.")

        source_path = checkout / "rendu" / exercise.slug / exercise.source
        if not source_path.is_file():
            raise GradeError(f"Não encontrei rendu/{exercise.slug}/{exercise.source} no push.")
        candidate = work / exercise.source
        shutil.copyfile(source_path, candidate)
        binary = work / "candidate"

        if exercise.function_harness is not None:
            harness = work / "grader.c"
            harness.write_text(exercise.function_harness, encoding="utf-8")
            harness_object = work / "grader.o"
            harness_compile = _run(
                ["gcc", "-Wall", "-Wextra", "-Werror", "-c", str(harness), "-o", str(harness_object)],
                cwd=work,
                timeout=10,
                apply_limits=False,
            )
            if harness_compile.returncode != 0:
                detail = _short(harness_compile.stderr or harness_compile.stdout or "falha sem diagnóstico")
                raise GradeError(f"Erro interno: grader.c não compilou: {detail}")

            candidate_object = work / "candidate.o"
            compile_result = _run(
                ["gcc", "-Wall", "-Wextra", "-Werror", "-c", str(candidate), "-o", str(candidate_object)],
                cwd=work,
                timeout=10,
                apply_limits=False,
            )
            expected = exercise.function_expected or ""
            if compile_result.returncode != 0:
                return False, _short(compile_result.stderr or compile_result.stdout or "Falha de compilação.")

            link_result = _run(
                ["gcc", str(candidate_object), str(harness_object), "-o", str(binary)],
                cwd=work,
                timeout=10,
                apply_limits=False,
            )
            if link_result.returncode != 0:
                return False, _short(link_result.stderr or link_result.stdout or "Falha ao vincular a solução ao grader.")

            result = _run([str(binary)], cwd=work)
            if result.returncode != 0:
                return False, f"O programa terminou com código {result.returncode}."
            if result.stdout != expected:
                return False, f"Saída inesperada. Esperado: {expected!r}; recebido: {result.stdout!r}."
            return True, "Todos os casos passaram."

        compile_result = _run(
            ["gcc", "-Wall", "-Wextra", "-Werror", str(candidate), "-o", str(binary)],
            cwd=work,
        )
        if compile_result.returncode != 0:
            return False, _short(compile_result.stderr or compile_result.stdout or "Falha de compilação.")
        for arguments, expected in exercise.cases:
            result = _run([str(binary), *arguments], cwd=work)
            if result.returncode != 0:
                return False, f"O programa terminou com código {result.returncode} no caso {arguments!r}."
            if result.stdout.rstrip("\n") != expected:
                return False, f"Caso {arguments!r}: esperado {expected!r}, recebido {result.stdout!r}."
        return True, f"Todos os {len(exercise.cases)} casos passaram."


def publish_next_subject(
    slug: str,
    repository_url: str,
    repository: Path = REPOSITORY,
    *,
    subject_prefix: str = "subjects",
) -> str:
    """Add the next exercise to subjects/ in a fresh clone and push it to the single repo."""
    source = SUBJECT_SOURCE_ROOT / slug
    with tempfile.TemporaryDirectory(prefix="examshell-publish-") as temp_dir:
        checkout = Path(temp_dir) / "exam"
        _clone_exam_repo(repository_url, checkout)
        destination = checkout / subject_prefix / slug
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination)
            add = subprocess.run(
                ["git", "-C", str(checkout), "add", str(destination.relative_to(checkout))],
                capture_output=True,
                text=True,
                check=False,
            )
            if add.returncode:
                raise GradeError(add.stderr.strip() or "Não consegui preparar o próximo enunciado.")
            commit = subprocess.run(
                ["git", "-C", str(checkout), "commit", "-m", f"Publish subject {slug}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if commit.returncode:
                raise GradeError(commit.stderr.strip() or "Não consegui criar o commit do próximo enunciado.")
            push = subprocess.run(
                ["git", "-C", str(checkout), "push", "origin", "master"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if push.returncode:
                raise GradeError(push.stderr.strip() or "Não consegui enviar o próximo enunciado ao Git.")

    commit_result = subprocess.run(
        ["git", f"--git-dir={repository}", "rev-parse", "--verify", "refs/heads/master"],
        capture_output=True,
        text=True,
        check=False,
    )
    if commit_result.returncode:
        raise GradeError("Não consegui ler o commit publicado no repositório.")
    return commit_result.stdout.strip()


def _short(text: str, limit: int = 1200) -> str:
    normalized = text.strip()
    if len(normalized) > limit:
        normalized = normalized[:limit] + "…"
    return normalized
