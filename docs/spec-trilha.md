# Spec — API actions da trilha (depois do diagnóstico)

Degrau 1–2 (nativo + Custom Query). Conexão `db`, provider `security_db`. Sem custom module.
Mesmas convenções de [spec-diagnostico.md](spec-diagnostico.md): erro = step **Response** com
`{"error": "..."}`; Custom Query com `:P1::int` quando o parâmetro entra em `insert/select` ou comparação.
O formato que a página `/trilha` consome está em [contrato-trilha.md](contrato-trilha.md); este spec diz como
as actions fazem isso.

Fluxo: `diagnostic/finish` cria a trilha → `path/current` → aluno responde a questão de prática →
`activity/complete` (corrige no servidor) → `path/current` … `progress/report` a qualquer momento.
O ExamShell (Python) usa as mesmas actions com o cookie de sessão do `POST /api/auth/login`.

## Modelo usado

- Trilha ativa: `user_path` com `user_id = {{security_db.identity}}` e `is_active` (a mais recente).
- Passos: `user_path_step` (`position` 1..m, único por trilha).
- Estado: `activity_progress` (único por `user_id, activity_id`). Status: `pending`, `failed` (última resposta errada), `done`.
  Sem linha de progresso conta como `pending`.
- Prática: 1 `question` por atividade com `kind = 'practice'` e `source_ref = 'activity:<activity.id>'`
  (sem coluna nova), 4 `question_option` com `feedback` nas erradas. Seed: `.wappler/seeds/db/trilha_pratica.js`
  (idempotente, roda depois do `diagnostico_demo`). O diagnóstico continua filtrando `kind = 'diagnostic'`.

Todas as actions começam com **Security → Security Restrict** → `security_db` (sem login URL → 401) e todo SQL
filtra por `{{security_db.identity}}`.

## `path/current` (GET)

1. Restrict.
2. Custom Query `path_rows` → Set Value `query_path` = `{{path_rows[0]}}` (output). Sem trilha: vazio, 200.
3. Custom Query `query_steps` (output, `:P1 = {{query_path.id}}`, `:P2 = identity`): passos em ordem de `position`
   com atividade, habilidade, `status`/`attempts`/`completed_at` e a questão de prática (`question_id`, `question`,
   `options` = json `[{id, text, position}]`, **sem `is_correct`**; `left join lateral` → `null` se não houver).
4. Set Value `total` = `{{query_steps.count()}}`, `done` = `{{query_steps.where('status', '==', 'done').count()}}`,
   `next` = `{{query_steps.where('status', '!=', 'done')[0]}}` (para o ExamShell; a página calcula sozinha).

> Atenção: no **servidor** o formatter é `where(prop, operador, valor)`; no App Connect é `where(prop, valor, operador)`.

## `path/next` (GET) — para o ExamShell

Formato em [contrato-examshell.md](contrato-examshell.md). Restrict → Custom Query `query_next` (trilha ativa,
`done`/`total`, primeiro passo com `status <> 'done'`; campos do passo `null` e `finished = true` quando acaba)
→ vazio: 404 `Nenhuma trilha ativa` → Set Value `next` = `{{query_next[0]}}`. Mesma regra do `path/current`; o
site usa o `path/current`.

## `activity/complete` (POST `activity_id`, `option_id` ou `correct`)

Opcional `source` (padrão `web`; o ExamShell manda `examshell`). Mande como formulário: o `core:required`
do Wappler recusa número JSON.

`correct` (boolean, **não** obrigatório, texto `true`/`false`): resultado do `grademe`. Só vale com
`source=examshell`. Nesse caso ele decide o resultado e o `option_id` não é exigido, mesmo que a atividade tenha
questão de prática. `true`/`1` = passou; outro valor = falhou (normalizado na expressão, não depende do `::boolean`).

1. Restrict.
2. Custom Query `query_step`: passo da trilha ativa com esse `activity_id` + `question_id` da prática.
   Vazio → 404 `Atividade fora da trilha ativa`.
3. Condition `{{query_step[0].question_id && !($_POST.source == 'examshell' && $_POST.correct != null)}}`:
   - sem `option_id` → 400 `Escolha uma alternativa`;
   - Custom Query `answer` (output): `is_correct`, `feedback` (só se errou), `explanation` da questão (só se acertou);
   - vazio → 400 `Alternativa não pertence à questão da atividade`.
   Atividade sem questão de prática: conta como acerto (o contrato antigo, só `activity_id`).
4. Custom Query `progress` (upsert, output),
   `:P3 = {{$_POST.source == 'examshell' && $_POST.correct != null ? ($_POST.correct == 'true' || $_POST.correct == true) : (query_step[0].question_id ? answer[0].is_correct : true)}}`:
   `attempts + 1`; `status` = `done` ou `failed`; `completed_at` mantém a primeira conclusão, `null` se errou.
5. Condition `{{progress[0].status == 'failed'}}` → reforço:
   1. Custom Query `reinforcement` (output): atividade da mesma habilidade com `level_n = nível - 1` (menor `id`) e
      `in_path`. Nível 1 → vazio → sem reforço.
   2. Condition `{{reinforcement[0]}}`:
      - `reopen_progress`: progresso do reforço volta a `pending`.
      - Condition `{{!reinforcement[0].in_path}}` → `shift_steps` → `insert_reinforcement` → `unshift_steps`:
        insere o reforço **na posição do passo errado** e empurra os seguintes (posições negativas no meio por causa
        do `unique (user_path_id, position)`).
      - Já na trilha (ex.: errou A2 depois de concluir A1): só reabre; ele volta a ser o próximo por ter posição menor.

## `progress/report` (GET)

1. Restrict.
2. Custom Query `query_path` → Set Value `path` (output): `user_path_id`, `started_at`, `total`, `done`, `failed`,
   `percent`, `finished`, `reason`. Vazio → 404 `Nenhuma trilha ativa`.
3. Custom Query `skills` (output): por habilidade (`sort_order`): `total`, `done`, `failed`, `attempts`, `percent`,
   `level_reached` (maior nível `done`, 0 se nenhum).

## Como testar (curl)

```bash
curl -c ck.txt -d "username=bruno&password=demo123" http://localhost:8100/api/auth/login
curl -b ck.txt http://localhost:8100/api/path/current
curl -b ck.txt -d "activity_id=19&option_id=66" http://localhost:8100/api/activity/complete
curl -b ck.txt http://localhost:8100/api/progress/report
```

Testado (Bruno, 2026-10-23): sem cookie 401; sem `option_id` 400; alternativa de outra questão 400; A1 errada →
`failed`, sem reforço; A1 certa → `done` + explicação; A2 errada → reabre A1 (próximo = A1); M2 errada → M1 inserido
na posição 4 (total 6 → 7); `options` sem `is_correct`.
ExamShell (Ana, atividade 13): `correct=false&source=examshell` → `failed`; `correct=true` → `done`; sem `source` → 400
como antes; atividade 14 `correct=false` → `failed` + P1 reaberto; `correct=1` → `done`. Depois de salvar os JSONs, abrir e salvar cada action uma vez no Wappler.
