# Spec — API actions do diagnóstico

Degrau 1–2 (nativo + Custom Query). Tudo criado no **Server Connect** do Wappler, conexão `db`.
Nenhum custom module é necessário.

Fluxo: `start` → (`question` → `answer`) × 5 → `finish`.

```
/diagnostico                      /resultado/:attempt_id
  start ─► question ─► answer ─┐     ▲
            ▲                  │     │
            └──── (até 5) ─────┘──► finish (score, trilha, explicação)
```

## Pré-requisitos (antes de testar)

1. **Banco de questões**: 5 linhas em `question` com `kind = 'diagnostic'` e `skill_id` preenchido
   (sugestão: 2 ponteiros, 2 memória, 1 algoritmos), cada uma com alternativas em `question_option`
   (uma com `is_correct = true`). A ordem do diagnóstico é `question.id`.
   Nas alternativas erradas, preencha `question_option.feedback` com a confusão que ela revela
   (ex.: "confunde `&x` (endereço) com `*x` (valor)").
2. **Banco de atividades**: em `activity`, pelo menos 1 atividade por habilidade **em cada nível**
   (`level_n` 1, 2 e 3) → mínimo 9. A trilha é montada a partir delas (migration
   `trilha personalizada`); `learning_path`/`learning_path_step` não são usadas neste fluxo.
3. **Variáveis de ambiente** (*Workflows/Project Settings → Server Connect → Environment Variables*,
   ou `.env` do target): `OPENAI_API_KEY` e `OPENAI_MODEL`. Nunca colocar a chave no JSON da action.

Faça 1 e 2 pelos **Seeds** do Database Manager.

## Convenções

- Pasta: *Server Connect → API → New Folder* `diagnostic`.
- Respostas de erro: step **Core Actions → Response** com `status` e `data` `{"error": "..."}`.
  No front, tratar com `dmx-on:invalid` (400) e `dmx-on:done` + checar status (ver gotchas).
- Custom Query: parâmetros `:P1`, `:P2`… definidos na aba **Parameters** da query.
  **Não** escreva `:Px` dentro de comentário SQL. O mesmo `:P1` pode aparecer várias vezes no SQL
  (confirmado em `lib/modules/dbupdater.js`: cada ocorrência vira um `?` com o mesmo valor).
  Casts `::int`/`::text` são seguros (não são confundidos com parâmetro).
- `is_correct` **nunca** sai para o navegador durante o diagnóstico.

## Autenticação (todas as actions)

O aluno é sempre o **logado** no Security Provider `security_db` (login em `api/auth/login`).
Nenhuma action recebe `user_id` do navegador.

O provider é global (`app/modules/global.json` → `SecurityProviders/security_db`), então
`{{security_db.identity}}` (= `user.id` do aluno logado) está disponível em qualquer action, sem
step extra.

Primeiro step de **toda** action do diagnóstico:

| # | Step (caminho na IDE) | Nome | Configuração |
|---|---|---|---|
| A | Security Provider → **Security Restrict** | — | Provider `security_db`; **sem** Login URL nem permissões → sem login responde **401** |

Nas tabelas abaixo, os steps começam depois de A.

- Tentativa de outro aluno: toda busca de `diagnostic_attempt` filtra também
  `user_id = {{security_db.identity}}`. Para quem não é dono, a tentativa "não existe" (404/409); não há
  como descobrir tentativas alheias trocando o `attempt_id`.
- No front, tratar 401 como "faça login" (`dmx-on:unauthorized` no Server Connect).

---

## 1. `diagnostic/start` — POST

Cria uma tentativa nova para o aluno logado e fecha as tentativas abertas dele.

**Globals → $_POST**: nenhum (o aluno vem de `{{security_db.identity}}`).

| # | Step (caminho na IDE) | Nome | Configuração |
|---|---|---|---|
| 1 | Database Actions → **Database Query** (Single) | `query_user` | tabela `user`, colunas `id`, `name`; condição `id = {{security_db.identity}}` |
| 2 | Core Actions → **Condition** | — | `{{!query_user}}` → **Then**: Response `404` `{"error":"Aluno não encontrado"}` (sessão de um usuário apagado) |
| 3 | Database Actions → **Update** | `close_open` | tabela `diagnostic_attempt`; `status = 'abandoned'`; condições `user_id = {{security_db.identity}}` **e** `status = 'in_progress'` |
| 4 | Database Actions → **Insert** | `insert_attempt` | tabela `diagnostic_attempt`; `user_id = {{security_db.identity}}`, `status = 'in_progress'` |
| 5 | Database Actions → **Custom Query** | `query_total` | SQL abaixo |
| 6 | Core Actions → **Set Value** (Output ✔) | `attempt_id` | `{{insert_attempt.identity}}` |

`query_total` (marque Output ✔):

```sql
select count(*)::int as total from question where kind = 'diagnostic'
```

**Saída esperada**: `{ "attempt_id": 7, "query_total": [{ "total": 5 }] }`

---

## 2. `diagnostic/question` — GET

Devolve a próxima questão **não respondida** da tentativa, com as alternativas (sem gabarito).

**Globals → $_GET**: `attempt_id` (number, required).

| # | Step | Nome | Configuração |
|---|---|---|---|
| 1 | Database Query (Single) | `query_attempt` | tabela `diagnostic_attempt`; condições `id = {{$_GET.attempt_id}}` **e** `user_id = {{security_db.identity}}` |
| 2 | Condition | — | `{{!query_attempt}}` → Response `404` `{"error":"Tentativa não encontrada"}` |
| 3 | Condition | — | `{{query_attempt.status != 'in_progress'}}` → Response `409` `{"error":"Tentativa encerrada"}` |
| 4 | Custom Query (Output ✔) | `query_next` | SQL abaixo, `:P1 = {{$_GET.attempt_id}}` |
| 5 | Condition | — | `{{!query_next[0]}}` → **Then**: Set Value `done` = `{{true}}` (Output ✔) |
| 6 | Database Query (Multiple, Output ✔) | `query_options` | tabela `question_option`; colunas **só** `id`, `text`, `position`; condição `question_id = {{query_next[0].id}}`; ordem `position ASC` |

> Coloque o step 6 no **Else** do step 5 (só busca alternativas quando há questão).

`query_next`:

```sql
select q.id, q.statement, q.difficulty,
       s.code as skill_code, s.title as skill_title,
       (select count(*) from diagnostic_answer da where da.attempt_id = :P1)::int as answered,
       (select count(*) from question where kind = 'diagnostic')::int as total
from question q
join skill s on s.id = q.skill_id
where q.kind = 'diagnostic'
  and not exists (
    select 1 from diagnostic_answer da
    where da.attempt_id = :P1 and da.question_id = q.id
  )
order by q.id
limit 1
```

**Saída esperada**: `query_next[0]` com `statement`, `answered` (para a barra "2 de 5") e
`query_options` com as alternativas. Quando acabar: `{ "done": true }` → front chama `finish`.

---

## 3. `diagnostic/answer` — POST

Grava uma resposta. O acerto é calculado **no servidor** a partir de `question_option.is_correct`.

**Globals → $_POST**: `attempt_id`, `question_id`, `option_id` (todos number, required).

| # | Step | Nome | Configuração |
|---|---|---|---|
| 1 | Database Query (Single) | `query_attempt` | `diagnostic_attempt` onde `id = {{$_POST.attempt_id}}` **e** `user_id = {{security_db.identity}}` **e** `status = 'in_progress'` |
| 2 | Condition | — | `{{!query_attempt}}` → Response `409` `{"error":"Tentativa inexistente ou encerrada"}` |
| 3 | Custom Query | `query_option` | SQL abaixo, `:P1 = {{$_POST.option_id}}`, `:P2 = {{$_POST.question_id}}` |
| 4 | Condition | — | `{{!query_option[0]}}` → Response `400` `{"error":"Alternativa não pertence à questão"}` |
| 5 | Database Query (Single) | `query_existing` | `diagnostic_answer` onde `attempt_id = {{$_POST.attempt_id}}` **e** `question_id = {{$_POST.question_id}}` |
| 6 | Condition | — | `{{query_existing}}` → Response `409` `{"error":"Questão já respondida"}` |
| 7 | Insert | `insert_answer` | `diagnostic_answer`: `attempt_id = {{$_POST.attempt_id}}`, `user_id = {{security_db.identity}}`, `question_id = {{$_POST.question_id}}`, `option_id = {{$_POST.option_id}}`, `is_correct = {{query_option[0].is_correct}}` |
| 8 | Custom Query (Output ✔) | `query_progress` | SQL abaixo, `:P1 = {{$_POST.attempt_id}}` |

`query_option`:

```sql
select o.id, o.is_correct
from question_option o
join question q on q.id = o.question_id
where o.id = :P1 and o.question_id = :P2 and q.kind = 'diagnostic'
```

`query_progress`:

```sql
select (select count(*) from diagnostic_answer where attempt_id = :P1)::int as answered,
       (select count(*) from question where kind = 'diagnostic')::int as total
```

**Saída esperada**: `{ "query_progress": [{ "answered": 3, "total": 5 }] }` — sem dizer se acertou.

> O step 6 evita o erro 500 do índice único `(attempt_id, question_id)` se o aluno clicar duas vezes.

---

## 4. `diagnostic/finish` — POST

Fecha a tentativa, calcula o score, **monta uma trilha própria para o aluno**, prepara o
progresso e gera a explicação personalizada com a OpenAI.

**Globals → $_POST**: `attempt_id` (number, required).

### Regra da trilha personalizada (determinística — view `attempt_path_plan`)

1. Score por habilidade = acertos ÷ respondidas (view `attempt_skill_score`).
2. Ponto de partida de cada habilidade:
   score < 0,5 → nível 1 (atividades 1, 2, 3) · 0,5 a < 1 → nível 2 (2, 3) · 1 → nível 3 (só 3).
3. Ordem: habilidade **mais fraca primeiro**; empate por `skill.sort_order`
   (ponteiros → memória → algoritmos, porque memória depende de ponteiros).
4. Dentro da habilidade: `level_n`, depois `activity.id`.

Exemplo validado no banco: **Ana** (erra ponteiros) → P1 → P2 → P3 → M3 → A3;
**Bruno** (erra algoritmos e 1 de memória) → A1 → A2 → A3 → M2 → M3 → P3.

A regra é editável em um único lugar (a view, via migration). A IA **só explica**; ela não decide.
Assim a demo é reproduzível.

| # | Step | Nome | Configuração |
|---|---|---|---|
| 1 | Database Query (Single) | `query_attempt` | `diagnostic_attempt` onde `id = {{$_POST.attempt_id}}` **e** `user_id = {{security_db.identity}}` **e** `status = 'in_progress'` |
| 2 | Condition | — | `{{!query_attempt}}` → Response `409` `{"error":"Tentativa inexistente ou encerrada"}` |
| 3 | Custom Query | `query_progress` | mesmo SQL do `answer`, `:P1 = {{$_POST.attempt_id}}` |
| 4 | Condition | — | `{{query_progress[0].answered < query_progress[0].total}}` → Response `400` `{"error":"Diagnóstico incompleto"}` |
| 5 | Update | `update_attempt` | `diagnostic_attempt` onde `id = {{$_POST.attempt_id}}`: `status = 'finished'`, `finished_at = {{NOW_UTC}}` (global do runtime, `lib/core/parser.js`) |
| 6 | Custom Query (Output ✔) | `query_scores` | SQL abaixo, `:P1 = {{$_POST.attempt_id}}` |
| 7 | Custom Query (Output ✔) | `query_plan` | SQL abaixo, `:P1 = {{$_POST.attempt_id}}` |
| 8 | Condition | — | `{{!query_plan[0]}}` → Response `500` `{"error":"Nenhuma atividade cadastrada para montar a trilha"}` |
| 9 | Update | `deactivate_paths` | `user_path` onde `user_id = {{query_attempt.user_id}}`: `is_active = {{false}}` |
| 10 | Custom Query | `insert_user_path` | SQL abaixo |
| 10b | Custom Query | `insert_steps` | SQL abaixo — copia o plano para `user_path_step` |
| 10c | Custom Query | `query_mistakes` | SQL abaixo — erros do aluno com o `feedback` da alternativa |
| 10d | Custom Query | `query_first_step` | SQL abaixo — título e enunciado da 1ª atividade, para o `primeiro_foco` |
| 11 | Custom Query | `seed_progress` | SQL abaixo |
| 12 | Core Actions → **Try / Catch** | — | **Try**: steps 12a–12d. **Catch**: steps 12e–12g |
| 12a | API → **API Action** | `api_explain` | ver configuração abaixo; **Throw Errors ✔**, **Pass Errors ✘**, Timeout `20000` |
| 12b | Condition | — | `{{api_explain.data.choices[0].finish_reason != 'stop' \|\| api_explain.data.choices[0].message.refusal}}` → **Then**: Core Actions → **Throw Error** `Resposta da IA incompleta ou recusada` |
| 12c | Set Value (Output ✔) | `explanation` | `{{api_explain.data.choices[0].message.content.parseJSON()}}` |
| 12d | Set Value (Output ✔) | `explanation_source` | `openai` |
| 12e | *(Catch)* Custom Query | `query_fallback` | SQL abaixo, `:P1 = {{$_POST.attempt_id}}` |
| 12f | *(Catch)* Set Value (Output ✔) | `explanation` | `{{query_fallback[0].feedback}}` |
| 12g | *(Catch)* Set Value (Output ✔) | `explanation_source` | `fallback` |
| 13 | Custom Query | `save_explanation` | SQL abaixo |
| 14 | Set Value (Output ✔) | `user_path_id` | `{{insert_user_path[0].id}}` |

> Não é preciso declarar `explanation` antes do Try: Try/Catch roda no mesmo escopo da action
> (testado). Os Set Value têm Output ✔; vale o último que rodar.

Na tabela, `\|\|` é só o escape do Markdown: no Wappler digite `||`.

Por que cada opção do step 12:

- **Pass Errors ✘**: com o padrão (✔), um 4xx/5xx da OpenAI (chave inválida, cota, modelo
  errado) é **repassado direto ao navegador** e a action para ali (`lib/modules/api.js`).
- **Throw Errors ✔**: transforma esse 4xx/5xx (e o timeout) em exceção → cai no Catch.
- **12b**: a OpenAI responde 200 mesmo quando corta a resposta (`finish_reason = 'length'`) ou
  recusa (`message.refusal`). Nesses casos não há JSON válido; o Throw Error leva ao Catch.
- **12c**: se o conteúdo não for JSON, `parseJSON()` lança exceção → também cai no Catch.
- Resultado: `explanation` **sempre** sai com o mesmo formato (o do schema), venha da IA ou do
  fallback. O front não precisa de dois layouts.

`query_scores` — mesma ordem da trilha (mais fraca primeiro):

```sql
select ass.skill_id, ass.skill_code, ass.answered, ass.correct, ass.score,
       round(coalesce(ass.score, 0) * 100)::int as pct
from attempt_skill_score ass
join skill s on s.id = ass.skill_id
where ass.attempt_id = :P1
order by ass.score asc nulls first, s.sort_order asc
```

`query_plan` — a trilha montada:

```sql
select position, activity_id, activity_title, level_n, skill_code, start_level, reason
from attempt_path_plan
where attempt_id = :P1
order by position
```

`insert_user_path` — `:P1 = {{query_attempt.user_id}}`, `:P2 = {{$_POST.attempt_id}}`
(`learning_path_id` fica vazio: a trilha é própria do aluno):

```sql
insert into user_path (user_id, attempt_id, is_active, reason)
select :P1::int, :P2::int, true,
       jsonb_build_object(
         'rule', 'nivel por score (<0.5:1, <1:2, 1:3); mais fraca primeiro; empate por sort_order',
         'scores', (
           select jsonb_agg(jsonb_build_object(
             'skill', skill_code, 'correct', correct, 'answered', answered, 'score', score
           ) order by skill_id)
           from attempt_skill_score where attempt_id = :P2::int
         )
       )
returning id
```

`insert_steps` — `:P1 = {{insert_user_path[0].id}}`, `:P2 = {{$_POST.attempt_id}}`:

```sql
insert into user_path_step (user_path_id, activity_id, skill_id, position, reason)
select :P1::int, activity_id, skill_id, position, reason
from attempt_path_plan
where attempt_id = :P2::int
```

`query_mistakes` — `:P1 = {{$_POST.attempt_id}}`:

```sql
select s.code as skill_code, q.statement, o.text as chosen,
       (select c.text from question_option c
        where c.question_id = q.id and c.is_correct limit 1) as correct_answer,
       o.feedback
from diagnostic_answer da
join question q on q.id = da.question_id
join skill s on s.id = q.skill_id
join question_option o on o.id = da.option_id
where da.attempt_id = :P1 and not da.is_correct
order by q.id
```

`query_first_step` — `:P1 = {{$_POST.attempt_id}}`:

```sql
select a.title, a.content
from attempt_path_plan p
join activity a on a.id = p.activity_id
where p.attempt_id = :P1
order by p.position
limit 1
```

`seed_progress` — cria as linhas de progresso da trilha (não duplica se o aluno refizer;
atividade já concluída continua concluída); `:P1 = {{query_attempt.user_id}}`,
`:P2 = {{insert_user_path[0].id}}`:

```sql
insert into activity_progress (user_id, activity_id, status)
select :P1::int, activity_id, 'pending'
from user_path_step
where user_path_id = :P2::int
on conflict (user_id, activity_id) do nothing
```

`api_explain` (API Action):

- **URL**: `https://api.openai.com/v1/chat/completions` — **Method**: POST — **Data Type**: JSON
- **Headers**: `Authorization` = `Bearer {{$_ENV.OPENAI_API_KEY}}`
- **Body** (JSON):

```json
{
  "model": "{{$_ENV.OPENAI_MODEL}}",
  "temperature": 0.3,
  "messages": [
    {
      "role": "system",
      "content": "Você é tutor de linguagem C e fala com o estudante em português, na segunda pessoa (\"você\"), em tom encorajador. Use só os dados enviados; não invente notas, questões nem atividades. A trilha já foi montada pelo sistema: explique, não altere.\nRegras:\n- Cada campo de texto tem no máximo 25 palavras.\n- Não use \"zero\", \"ruim\", \"fraco\" nem números decimais; fale em porcentagem ou em \"x de y\" quando precisar citar resultado.\n- Em cada confusão, explique só o erro da alternativa que o estudante escolheu, comparando com a resposta correta. Não cite outros erros possíveis da mesma questão.\nCampos:\n- resumo: 1 frase sobre o resultado geral, começando pelo que ele já domina.\n- confusoes: uma entrada por erro (lista vazia se não errou nada); confusao = a ideia errada, em linguagem simples; explicacao = por que a resposta correta é a correta.\n- por_que_comeca_aqui: 1 frase ligando o menor resultado à primeira atividade.\n- primeiro_foco: o que ele vai praticar na primeira atividade, com base no enunciado dela.\n- dica: 1 ação prática para estudar."
    },
    {
      "role": "user",
      "content": "Resultado por habilidade: {{query_scores.toJSON()}}. Erros (alternativa escolhida, resposta correta e a confusão que revela): {{query_mistakes.toJSON()}}. Trilha montada: {{query_plan.toJSON()}}. Primeira atividade: {{query_first_step[0].toJSON()}}."
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "diagnostic_feedback",
      "strict": true,
      "schema": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "resumo",
          "confusoes",
          "por_que_comeca_aqui",
          "primeiro_foco",
          "dica"
        ],
        "properties": {
          "resumo": {
            "type": "string"
          },
          "confusoes": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "skill_code",
                "confusao",
                "explicacao"
              ],
              "properties": {
                "skill_code": {
                  "type": "string",
                  "enum": [
                    "ponteiros",
                    "memoria",
                    "algoritmos"
                  ]
                },
                "confusao": {
                  "type": "string"
                },
                "explicacao": {
                  "type": "string"
                }
              }
            }
          },
          "por_que_comeca_aqui": {
            "type": "string"
          },
          "primeiro_foco": {
            "type": "string"
          },
          "dica": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

Por que o prompt é assim (testado com Ana e Bruno, `gpt-4.1-mini`):

- `correct_answer` em `query_mistakes` + a regra "só o erro da alternativa escolhida": sem isso a
  IA misturava confusões de outras alternativas da mesma questão.
- `query_first_step` (enunciado): `primeiro_foco` passa a descrever o exercício real, não o título.
- Limite de 25 palavras, "você", sem "zero"/decimais, `pct` em `query_scores`: texto curto e
  encorajador para a demo. `temperature: 0.3`: respostas parecidas entre execuções.

Regras do schema (Structured Outputs com `strict: true`):

- Todo campo precisa estar em `required` e todo objeto precisa de `additionalProperties: false`;
  sem isso a OpenAI rejeita o request com 400 (cai no Catch).
- O `enum` de `skill_code` impede a IA de inventar habilidades. **Cadastrou uma habilidade nova
  em `skill`? Acrescente o `code` aqui.**
- `OPENAI_MODEL` precisa ser um modelo com suporte a Structured Outputs (ex.: `gpt-4o-mini` ou
  mais novo). Modelo sem suporte → 400 → Catch.
- Usamos `chat/completions` (e não a Responses API) porque o texto fica sempre em
  `choices[0].message.content`. Na Responses API a posição muda (`output[n]`) quando o modelo
  devolve itens de raciocínio, o que quebra um binding fixo no Wappler.

> `toJSON()` e `parseJSON()` existem no runtime (`lib/formatters/core.js`). Se não aparecerem no
> picker de formatters, digite a expressão à mão no campo — funciona igual.

`query_fallback` — mesmo formato do schema, montado só com dados do banco (o `feedback` das
alternativas erradas faz o papel de `confusoes`):

```sql
with first_step as (
  select skill_code, activity_title, reason
  from attempt_path_plan
  where attempt_id = :P1
  order by position
  limit 1
)
select jsonb_build_object(
  'resumo', 'Sua trilha começa por ' || f.skill_code
            || ', a habilidade em que você teve o menor acerto no diagnóstico.',
  'confusoes', coalesce((
    select jsonb_agg(jsonb_build_object(
             'skill_code', s.code,
             'confusao', o.feedback,
             'explicacao', 'Você escolheu "' || o.text || '" em: ' || q.statement
           ) order by q.id)
    from diagnostic_answer da
    join question q on q.id = da.question_id
    join skill s on s.id = q.skill_id
    join question_option o on o.id = da.option_id
    where da.attempt_id = :P1 and not da.is_correct and o.feedback is not null
  ), '[]'::jsonb),
  'por_que_comeca_aqui', f.reason,
  'primeiro_foco', f.activity_title,
  'dica', 'Faça as atividades na ordem: cada uma usa o que a anterior treinou.'
) as feedback
from first_step f
```

`save_explanation` — `:P1 = {{insert_user_path[0].id}}`, `:P2 = {{explanation.toJSON()}}`,
`:P3 = {{explanation_source}}`:

```sql
update user_path
set reason = reason || jsonb_build_object('ai_explanation', :P2::jsonb,
                                          'explanation_source', :P3::text)
where id = :P1::int
```

No front (`views/diagnostico.ejs`), `explanation` deixa de ser texto: use
`sc_finish.data.explanation.resumo`, `.por_que_comeca_aqui`, `.primeiro_foco`, `.dica` e um
`dmx-repeat="sc_finish.data.explanation.confusoes"` para a lista de confusões.

**Saída esperada**:

```json
{
  "query_scores": [
    { "skill_code": "ponteiros", "correct": 0, "answered": 2, "score": "0.00" },
    { "skill_code": "memoria",   "correct": 2, "answered": 2, "score": "1.00" },
    { "skill_code": "algoritmos","correct": 1, "answered": 1, "score": "1.00" }
  ],
  "query_plan": [
    { "position": 1, "activity_title": "P1", "reason": "ponteiros: score 0.00 -> começa no nível 1" },
    { "position": 4, "activity_title": "M3", "reason": "memoria: score 1.00 -> começa no nível 3" }
  ],
  "explanation": {
    "resumo": "Você foi bem em memória e algoritmos; o ponto fraco está em ponteiros.",
    "confusoes": [
      { "skill_code": "ponteiros", "confusao": "confunde `&x` (endereço) com `*x` (valor)", "explicacao": "…" }
    ],
    "por_que_comeca_aqui": "Ponteiros teve score 0, então a trilha começa no nível 1 (P1).",
    "primeiro_foco": "Diferenciar endereço e valor com `&` e `*`.",
    "dica": "Desenhe as variáveis e setas no papel antes de rodar o código."
  },
  "explanation_source": "openai",
  "user_path_id": 12
}
```

---

> `score` é `numeric` no Postgres e chega ao Wappler como **texto** (`"0.50"`). A ordenação já é
> feita no SQL; para comparar ou formatar no front, use `.toNumber()` antes
> (ex.: `{{score.toNumber() * 100}}%`).

> Parâmetros de Custom Query chegam ao Postgres sem tipo: em `insert ... select :P1, ...` use
> `:P1::int` para não depender da inferência.

## Status (2026-10-23)

As 4 actions existem em `app/api/diagnostic/`. `question`, `answer` e `finish` foram escritos em
JSON a pedido da Dani — **abrir e salvar cada uma uma vez no Wappler**. Passaram: Ana
(P1→P2→P3→M3→A3), Bruno (A1→A2→A3→M2→M3→P3), todos os erros do item 6 e o fallback do item 7
(`explanation_source = "fallback"`, gravado como objeto) e o item 8 com `OPENAI_MODEL =
gpt-4.1-mini` (`explanation_source = "openai"`, `confusoes` coerentes com os erros de cada aluno).

## Como testar (as duas personas)

Pelo navegador ou Postman, com o servidor do Wappler rodando (`http://localhost:8100`).
Dados: seed `.wappler/seeds/db/diagnostico_demo.js` (alunos `ana` e `bruno`, senha `demo123`).
As chamadas precisam do **cookie de sessão** do login (no Postman, o cookie jar guarda sozinho).

0. `POST /api/auth/login` `username=ana&password=demo123`.
1. `POST /api/diagnostic/start` (sem corpo) → anote `attempt_id`.
2. 5× `GET /api/diagnostic/question?attempt_id=…` + `POST /api/diagnostic/answer`
   — **Ana** erra as de ponteiros e acerta o resto.
3. `POST /api/diagnostic/finish` → trilha **P1 → P2 → P3 → M3 → A3**.
   No seed, Ana erra Q1 e Q2.
4. Logue como `bruno` e repita errando algoritmos e 1 de memória (Q3 e Q5 no seed)
   → **A1 → A2 → A3 → M2 → M3 → P3**.
5. Conferir no Database Manager: `user_path` (2 linhas ativas), `user_path_step` com a sequência
   e o `reason` de cada passo, `activity_progress`, e a view `attempt_path_plan`.
6. Casos de erro: `finish` com 4 respostas → 400; `answer` repetido → 409;
   `option_id` de outra questão → 400; `question` após `finish` → 409;
   qualquer action sem login → 401; logado como Bruno, `question`/`answer`/`finish` com o
   `attempt_id` da Ana → 404/409 (a tentativa não aparece para ele).
7. Sem `OPENAI_API_KEY` (ou com `OPENAI_MODEL` inválido) → `finish` ainda responde 200, com
   `explanation_source = "fallback"` e `explanation` no mesmo formato, montado por `query_fallback`.
8. Com a chave válida → `explanation_source = "openai"`; confira que `confusoes` só traz
   habilidades do `enum` e que `user_path.reason.ai_explanation` foi gravado como objeto.

## Fora deste spec

- Cadastro de alunos e hash de senha: o seed grava `demo123` em texto puro (o `security_db` só
  verifica argon2 quando o `hash` começa com `$`, e o pacote `argon2` ainda não está instalado).
  Para produção: action de cadastro com *Crypto → Password Hash*.
- Clientes fora do navegador (ex.: ExamShell chamando `path/next`/`progress/report`) também vão
  precisar de sessão (login + cookie) ou de outro mecanismo de autenticação.
- Adaptação durante a trilha (errou a prática → inserir reforço do nível anterior): fica na
  action `activity/complete`, fora deste spec.
