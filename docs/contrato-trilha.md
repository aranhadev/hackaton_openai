# Contrato — o que a página /trilha (e o ExamShell) recebem das APIs

Front: `views/trilha.ejs`. Implementação: [spec-trilha.md](spec-trilha.md). Aluno sempre de
`{{security_db.identity}}` (Security Restrict no início → 401 sem login), erros com `{"error": "..."}`.

## 1. `path/current` — GET

Trilha ativa do aluno logado, com status e questão de prática de cada passo. Sem parâmetros.

| Saída | Tipo | Conteúdo |
|---|---|---|
| `query_path` | objeto | `user_path` ativo: `id`, `creation_dt`, `reason` (jsonb; a página lê `reason.ai_explanation.resumo`, `.primeiro_foco`, `.dica`) |
| `query_steps` | lista | um item por passo, em ordem de `position` |
| `total`, `done` | número | passos e passos com `status = 'done'` |
| `next` | objeto | primeiro passo com `status != 'done'` (`null` se a trilha acabou) |

Sem trilha ativa → `query_path` vazio e `query_steps` `[]` (200). A página mostra "faça o diagnóstico".

Campos de cada item de `query_steps` (e de `next`):

`position`, `reason`, `activity_id`, `title`, `level_n`, `kind`, `content`, `explanation`, `examshell_id`,
`skill_code`, `skill_title`, `status`, `attempts`, `completed_at`,
`question_id`, `question` (enunciado), `options` = `[{id, text, position}]` em ordem de `position`
(**sem** `is_correct`; `null` se a atividade não tem questão de prática).

`status`: `pending` | `failed` (errou a última resposta) | `done`.

## 2. `activity/complete` — POST

Corrige a resposta do aluno no servidor e atualiza o progresso.

**$_POST** (formulário): `activity_id` (required), `option_id` (alternativa escolhida; obrigatória quando o passo tem
`question_id`), `source` (opcional: `web` | `examshell`), `correct` (só com `source=examshell`: resultado do `grademe`,
dispensa o `option_id`; ver [contrato-examshell.md](contrato-examshell.md)).

Erros: 404 atividade fora da trilha ativa; 400 sem `option_id`; 400 alternativa que não é dessa questão.

Saída 200:

| Saída | Conteúdo |
|---|---|
| `answer[0]` | `option_id`, `is_correct`, `feedback` (só se errou: a confusão que a alternativa revela), `explanation` (só se acertou) |
| `progress[0]` | `activity_id`, `status` (`done`/`failed`), `attempts`, `completed_at` |
| `reinforcement` | só se errou: `[{activity_id, title, level_n, in_path}]` — atividade do nível anterior da mesma habilidade (vazio no nível 1) |

Errou com reforço: o reforço entra na trilha antes da atividade errada (ou, se já estava, volta a `pending`).
A página só precisa recarregar `path/current`: o próximo passo já é o reforço.

## 3. `progress/report` — GET (ExamShell / painel)

`path`: `user_path_id`, `started_at`, `total`, `done`, `failed`, `percent`, `finished`, `reason`.
`skills[]`: `skill_code`, `skill_title`, `total`, `done`, `failed`, `attempts`, `percent`, `level_reached`.
404 sem trilha ativa.
