# Contrato — integração ExamShell ↔ Trilha C

Para o ExamShell (Python, `C:\Users\dani\Documents\Dev\HackathonOpenAI`) seguir a **trilha
personalizada** do aluno, em vez da ordem fixa dos 5 exercícios, e devolver o resultado do
`grademe` para o app.

O app (Wappler) continua dono da trilha, do progresso e da regra de reforço. O ExamShell só
**pergunta qual é o próximo passo**, **avalia o código** e **avisa o resultado**.

```
aluno ──ssh──► ExamShell ──POST /api/auth/login──────────► app (cookie de sessão)
                  │      ──GET  /api/path/next───────────► próximo passo da trilha
                  │          examshell_id? → publica o subject do exercício
                  │          sem examshell_id → "sua próxima atividade é no site"
               grademe   ──POST /api/activity/complete───► done ou failed (+ reforço)
                         ──GET  /api/path/next───────────► próximo passo
```

## Variáveis de ambiente (ExamShell)

| Variável | Exemplo | Para quê |
|---|---|---|
| `TRILHA_API_URL` | `http://host.docker.internal:8100` (local) · `https://trilha.seudominio.com` (VPS) | Base das chamadas. Sem `/` no fim. **Obrigatória**: sem ela, o ExamShell volta para o modo de ordem fixa |
| `TRILHA_API_TIMEOUT` | `10` | Timeout em segundos de cada chamada |
| `TRILHA_SOURCE` | `examshell` | Valor do campo `source` no `activity/complete` |
| `EXAM_PASSWORD`, `EXAMSHELL_HOST_IP`, `EXAMSHELL_PUBLIC_GIT_URL` | — | Já existem no `docker-compose.yml` dele, sem mudança |

De dentro do container do ExamShell, o app local é `host.docker.internal:8100`, e **não**
`localhost`. No VPS, use a URL pública do app.

Nenhuma credencial de aluno vai em variável de ambiente: o aluno digita usuário e senha na
entrada do ExamShell.

## Autenticação

O app usa o **Security Provider do Wappler** (`security_db`) com **cookie de sessão**. O
ExamShell guarda o cookie (ex.: `requests.Session()`) e o manda em todas as chamadas.

### `POST /api/auth/login`

Formulário (`application/x-www-form-urlencoded`):

| Campo | Obrigatório | Valor |
|---|---|---|
| `username` | sim | usuário do aluno no app (ex.: `ana`) |
| `password` | sim | senha do aluno |
| `remember` | não | `true` para cookie persistente |

| Status | Corpo | O que o ExamShell faz |
|---|---|---|
| 200 | `{"identity": 5}` | Guarda o cookie e o `identity` (id do aluno) para mostrar no `status` |
| 401 | — | "Usuário ou senha inválidos" e pede de novo |

Qualquer chamada sem cookie válido responde **401 `Unauthorized`**. Se isso acontecer no meio
da sessão (cookie expirou), o ExamShell refaz o login.

## `GET /api/path/next`

Sem parâmetros. Devolve o **primeiro passo não concluído** da trilha ativa do aluno.

```json
{
  "next": {
    "user_path_id": 13,
    "done": 1,
    "total": 5,
    "finished": false,
    "position": 2,
    "activity_id": 14,
    "title": "P2 · Aritmética de ponteiros e vetores",
    "kind": "quiz",
    "level_n": 2,
    "skill_code": "ponteiros",
    "skill_title": "Ponteiros",
    "content": "Percorra `int v[5]` usando só um ponteiro (`p++`)…",
    "explanation": "`p + 1` avança `sizeof(*p)` bytes…",
    "examshell_id": null,
    "status": "pending",
    "attempts": 0,
    "reason": "ponteiros: score 0.00 -> começa no nível 1"
  }
}
```

| Situação | Resposta | O que o ExamShell faz |
|---|---|---|
| Passo com `examshell_id` | 200, `next.examshell_id = "ft_swap"` | Publica `subjects/subject/ft_swap/` e mostra `Passo {position} de {total} · {skill_title}` |
| Passo **sem** `examshell_id` | 200, `next.examshell_id = null` | "Sua próxima atividade (`{title}`) é no site: {TRILHA_API_URL}/trilha". `grademe` fica indisponível até o próximo `path/next` trazer um exercício |
| Trilha concluída | 200, `next.finished = true` (campos do passo `null`) | Mensagem de conclusão, igual ao `finish` atual |
| Aluno sem diagnóstico | 404 `{"error":"Nenhuma trilha ativa"}` | "Faça o diagnóstico em {TRILHA_API_URL}/diagnostico" |

`status` pode ser `pending` ou `failed`: neste caso, a última tentativa falhou. Use `attempts`
para mostrar "tentativa N".

Se o aluno errou e o app inseriu um **reforço**, o próximo `path/next` já devolve o reforço. O
ExamShell não precisa saber da regra: ele sempre publica o que vier em `next`.

## `POST /api/activity/complete`

Formulário, chamado **depois** do `grademe`:

| Campo | Obrigatório | Valor |
|---|---|---|
| `activity_id` | sim | `next.activity_id` do passo que estava publicado |
| `correct` | sim, para o ExamShell | `true` (passou) ou `false` (falhou). **Como texto** de formulário: o Wappler recusa boolean `false` em JSON |
| `source` | sim, para o ExamShell | `examshell` |
| `option_id` | não | só para atividades de quiz no site; o ExamShell não manda |

| Status | Corpo | O que o ExamShell faz |
|---|---|---|
| 200 | `progress[0]`: `{activity_id, status: "done"\|"failed", attempts, completed_at}` | Chama `path/next` e publica o que vier, seja o próximo passo, o reforço ou a mesma atividade |
| 404 | `{"error":"Atividade fora da trilha ativa"}` | A trilha mudou: o aluno refez o diagnóstico no site. Chama `path/next` de novo |
| 401 | `Unauthorized` | Refaz o login e repete a chamada |

O `grademe` **só** chama `activity/complete` depois de avaliar um push novo. Sem push novo, não
conta tentativa.

### ✅ Mudança no app (feita em 23/10)

A `activity/complete` aceita o resultado do `grademe`: com `source=examshell` e `correct` presente, o
`correct` decide `done`/`failed`, mesmo em atividade que também tem questão de prática no site (aí o
`option_id` não é exigido). `true`/`1` = passou; qualquer outro valor (`false`, `0`) = falhou.
Sem `source=examshell` nada muda: quiz pelo `option_id`, e atividade sem questão conta como `done`.

Na IDE: *$_POST* → `correct` (boolean, não obrigatório); step `progress` → `:P3` =
`{{$_POST.source == 'examshell' && $_POST.correct != null ? ($_POST.correct == 'true' || $_POST.correct == true) : (query_step[0].question_id ? answer[0].is_correct : true)}}`;
a Condition da questão virou `{{query_step[0].question_id && !($_POST.source == 'examshell' && $_POST.correct != null)}}`.

Conferido com a Ana (atividade 13): `correct=false` → `failed`; `correct=true` → `done`; sem `source` → 400
"Escolha uma alternativa" (igual a antes); atividade 14 com `correct=false` → `failed` + reforço (P1 reaberto,
`path/next` volta para P1).

## Mapeamento `examshell_id`

`activity.examshell_id` = o **`slug`** do exercício em `src/examshell/catalog.py`, com o mesmo
texto exato. Uma atividade aponta para no máximo um exercício.

Situação hoje: as 9 atividades têm `examshell_id` vazio, e o ExamShell tem 5 exercícios
(`ft_strlen`, `ft_swap`, `first_word`, `last_word`, `wdmatch`), **nenhum de memória**.

Mapeamento sugerido:

| Atividade (id) | Habilidade · nível | `examshell_id` | Por quê |
|---|---|---|---|
| P1 · Endereço (&) e valor (*) (13) | ponteiros · 1 | `ft_swap` | Troca valores via `*a`/`*b`: endereço × valor |
| P2 · Aritmética de ponteiros e vetores (14) | ponteiros · 2 | `ft_strlen` | Percorrer string com ponteiro até `\0` |
| P3 · Ponteiro para ponteiro (15) | ponteiros · 3 | — | Sem exercício hoje |
| M1 · Stack x heap (16) | memória · 1 | — | Conceitual, fica no site |
| M2 · malloc e free sem vazamento (17) | memória · 2 | **`ft_strdup` (novo)** | `malloc` do tamanho certo + cópia |
| M3 · realloc e uso após free (18) | memória · 3 | **`ft_range` (novo)** | Alocar vetor de tamanho calculado |
| A1 · Laços e limites de vetor (19) | algoritmos · 1 | `first_word` | Laço com limite e espaços |
| A2 · Busca linear em strings (20) | algoritmos · 2 | `wdmatch` | Busca de subsequência em string |
| A3 · Ordenação por inserção (21) | algoritmos · 3 | — | Sem exercício hoje |

`last_word` fica sem atividade e continua disponível no modo de ordem fixa.

Para gravar, coloque no seed `diagnostico_demo` (Database Manager → Seeds) ou rode no banco:

```sql
update activity set examshell_id = 'ft_swap'    where id = 13;
update activity set examshell_id = 'ft_strlen'  where id = 14;
update activity set examshell_id = 'first_word' where id = 19;
update activity set examshell_id = 'wdmatch'    where id = 20;
-- quando existirem no catalog.py:
-- update activity set examshell_id = 'ft_strdup' where id = 17;
-- update activity set examshell_id = 'ft_range'  where id = 18;
```

Os ids são do banco local. No VPS, use o `title` ou o seed, nunca o id fixo.

## O que muda no ExamShell (resumo para o colega)

1. **Cliente HTTP** (`src/examshell/trilha.py`): `login(user, pwd)`, `next()` e
   `complete(activity_id, correct)`, com `requests.Session` e timeout. Erros de rede viram
   mensagem amigável e não derrubam o shell.
2. **Entrada (`cli.py`)**: se `TRILHA_API_URL` existir, pedir usuário e senha do app, depois
   chamar `next()` e publicar o subject de `examshell_id`. Se não existir, manter o fluxo atual.
3. **`grademe`**: depois de avaliar, chamar `complete(next.activity_id, passou)` e então
   `next()`. Publicar o novo subject **só** se o `examshell_id` mudou.
4. **`status`**: mostrar `Passo {position} de {total}`, a habilidade e a tentativa.
5. **Catálogo**: adicionar `ft_strdup` e `ft_range` (memória).

## Como testar

```bash
curl -c ck.txt -d "username=ana&password=demo123" http://localhost:8100/api/auth/login
curl -b ck.txt http://localhost:8100/api/path/next
curl -b ck.txt -d "activity_id=13&correct=false&source=examshell" http://localhost:8100/api/activity/complete
curl -b ck.txt http://localhost:8100/api/path/next
```

Conferido em 23/10 no app local: login (200 com `identity`), `path/next` (formato acima), 401
sem cookie e 404 para atividade fora da trilha. O `correct=false` vindo do ExamShell já funciona (mudança acima). Para voltar a Ana e o Bruno ao estado inicial, use `demo/reset`.
