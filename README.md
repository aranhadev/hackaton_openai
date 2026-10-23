# Trilha C — trilha de estudo personalizada

Hackathon OpenAI · desafio **"Trilha de estudo personalizada"**.
Assunto: linguagem C — **ponteiros**, **gerenciamento de memória** e **algoritmos**.

## Problema

Quem estuda C trava em pontos diferentes: um aluno confunde endereço com valor, outro passa do fim
do vetor. Uma lista de exercícios igual para todos faz um repetir o que já sabe e o outro pular o
que ainda não entendeu.

## Solução

1. **5 questões diagnósticas** (2 de ponteiros, 2 de memória, 1 de algoritmos). Cada alternativa
   errada tem um `feedback` com a confusão que ela revela. O acerto é calculado no servidor; o
   gabarito nunca vai para o navegador.
2. **Uma regra determinística monta a trilha** (view `attempt_path_plan` no Postgres):
   - score por habilidade = acertos ÷ respondidas;
   - score < 0,5 → começa no nível 1 · < 1 → nível 2 · = 1 → só o nível 3;
   - habilidade **mais fraca primeiro**; empate por `skill.sort_order`
     (ponteiros → memória → algoritmos, porque memória depende de ponteiros).

   A regra fica em um só lugar e a demo é reproduzível: mesmas respostas, mesma trilha.
3. **A IA só explica.** O `gpt-4.1-mini` recebe os scores, os erros (alternativa escolhida +
   resposta correta + confusão) e a trilha já montada, e devolve um JSON validado por schema
   (Structured Outputs, `strict: true`): `resumo`, `confusoes[]`, `por_que_comeca_aqui`,
   `primeiro_foco`, `dica`. Ela não altera a trilha.
4. **Fallback garantido.** Se a OpenAI falhar (chave, cota, modelo, timeout, resposta cortada ou
   recusada), a explicação é montada com os dados do banco **no mesmo formato**. A resposta continua
   200; o campo `explanation_source` diz `openai` ou `fallback`.
5. **Prática, progresso e reforço.** A trilha fica gravada com o motivo de cada passo. Em `/trilha`
   o aluno responde uma questão de prática por atividade e o servidor corrige: acertou → passo
   `done` e avança; errou → passo `failed`, com a confusão da alternativa escolhida, e a atividade
   do nível anterior da mesma habilidade vira reforço — inserida antes da atividade errada ou, se já
   estava na trilha, reaberta (no nível 1 não há reforço). `progress/report` resume o progresso por
   habilidade.

## Personas da demo

| Persona | Erra no diagnóstico | Trilha |
|---|---|---|
| **Ana** (`ana` / `demo123`) | Q1 e Q2 — ponteiros | P1 → P2 → P3 → M3 → A3 |
| **Bruno** (`bruno` / `demo123`) | Q3 (memória) e Q5 (algoritmos) | A1 → A2 → A3 → M2 → M3 → P3 |

Ana tem 0 % em ponteiros e 100 % no resto: ponteiros desde o nível 1, depois só o desafio final
de memória e de algoritmos. Bruno tem 0 % em algoritmos e 50 % em memória: algoritmos desde o
nível 1, memória a partir do nível 2, ponteiros só no nível 3. Na demo, Bruno erra a prática de A2
e a trilha o manda de volta para A1 como reforço antes de tentar de novo.

Passo a passo da apresentação: [docs/roteiro-demo.md](docs/roteiro-demo.md).

## Arquitetura

```
Navegador (App Connect / EJS)          ExamShell (Python, colega)
  /diagnostico · /trilha                  path/next, activity/complete,
        │                                 progress/report
        │                                        │  (login + cookie de sessão)
        ▼                                        ▼
Wappler Server Connect (Node) ── Security Provider security_db (aluno logado)
  diagnostic/start → question → answer → finish
  path/current · path/next · activity/complete · progress/report · demo/reset
        │                                   │
        ▼                                   ▼
Postgres 17                             OpenAI chat/completions
  views attempt_skill_score,              gpt-4.1-mini, response_format json_schema
        attempt_path_plan (a regra)       (Try/Catch → fallback do banco)
  user_path, user_path_step,
  activity_progress
```

- **Wappler Server Connect**: todas as APIs são actions nativas (Database Query, Custom Query,
  Condition, Try/Catch, API Action), sem custom module. Toda action começa com *Security Restrict*:
  o aluno vem da sessão (`security_db.identity`), nunca de um `user_id` enviado pelo cliente.
- **Postgres**: a regra da trilha mora na view `attempt_path_plan` (migration `trilha personalizada`).
  `user_path.reason` guarda os scores, a regra aplicada e a explicação da IA (`ai_explanation`).
- **OpenAI Structured Outputs**: `chat/completions` com `json_schema` estrito; o `enum` de
  `skill_code` impede a IA de inventar habilidades. `temperature: 0.3` para respostas estáveis.

Detalhes: [docs/spec-diagnostico.md](docs/spec-diagnostico.md), [docs/spec-trilha.md](docs/spec-trilha.md),
[docs/contrato-trilha.md](docs/contrato-trilha.md) e [docs/contrato-examshell.md](docs/contrato-examshell.md).

### APIs

| Action | Método | O que faz |
|---|---|---|
| `auth/login` | POST `username`, `password` | abre a sessão |
| `diagnostic/start` | POST | cria a tentativa (encerra as abertas) |
| `diagnostic/question` | GET `attempt_id` | próxima questão não respondida, sem gabarito |
| `diagnostic/answer` | POST `attempt_id`, `question_id`, `option_id` | grava a resposta |
| `diagnostic/finish` | POST `attempt_id` | score, trilha, progresso inicial e explicação |
| `path/current` | GET | trilha ativa com status e questão de prática de cada passo (sem gabarito) — usada pela `/trilha` |
| `path/next` | GET | próximo passo da trilha ativa (`n de m`) — usada pelo ExamShell |
| `activity/complete` | POST `activity_id`, `option_id` (site) ou `correct` + `source=examshell` | corrige no servidor, grava `done`/`failed`; reforço se errou |
| `progress/report` | GET | progresso geral e por habilidade |
| `demo/reset` | POST | apaga tentativas, trilhas e progresso de Ana e Bruno (só com `DEMO_RESET_ENABLED=true` e `token` = `DEMO_RESET_TOKEN`) |

Clientes fora do navegador (ExamShell) usam o mesmo cookie de sessão do `auth/login` e mandam
`activity/complete` como form-urlencoded (não JSON), com o resultado do `grademe` em `correct`.

## Como rodar localmente

Requisitos: [Wappler](https://wappler.io) com Docker (o target **Development** sobe o Node na
porta `8100` e o Postgres 17 na `9911`).

1. Abra o projeto no Wappler e inicie o target **Development**.
2. **Database Manager** (conexão `db`): aplique as migrations e rode o seed
   `.wappler/seeds/db/diagnostico_demo.js` (5 questões, 9 atividades P1…A3, alunos Ana e Bruno) e,
   depois dele, `trilha_pratica.js` (1 questão de prática por atividade).
3. **Project Settings → Server Connect → Environment Variables** (target Development):
   - `OPENAI_API_KEY` — sua chave (nunca no JSON das actions nem no git);
   - `OPENAI_MODEL` — `gpt-4.1-mini` (precisa suportar Structured Outputs);
   - `DEMO_RESET_ENABLED` — `true` para liberar o `demo/reset`;
   - `DEMO_RESET_TOKEN` — segredo que o `demo/reset` exige no campo `token` do POST.
4. Abra cada action de `app/api/` uma vez no Wappler e salve (algumas foram escritas em JSON).
5. Acesse `http://localhost:8100/diagnostico` e entre como `ana` / `demo123`.

Teste rápido pela linha de comando:

```bash
curl -c ck.txt -d "username=ana&password=demo123" http://localhost:8100/api/auth/login
```

```bash
curl -b ck.txt http://localhost:8100/api/path/next
```

Sem a chave da OpenAI tudo funciona: o `finish` responde com `explanation_source = "fallback"`.

## Próximos passos

- **Tela de cadastro**, fora do MVP: a action `auth/register` (argon2) já existe. Senha nunca fica
  em texto puro: o seed grava hash argon2id e o banco recusa qualquer outra coisa (`user_hash_argon2`).
- **Página inicial** com dados reais (hoje é estática).
- **ExamShell**: o lado do app está pronto ([contrato](docs/contrato-examshell.md)); falta o
  cliente em Python, gravar `activity.examshell_id` das atividades e criar exercícios de memória.
  Avaliar autenticação por token em vez de cookie.
- **Mais conteúdo**: mais questões por habilidade e novas habilidades (cada nova precisa entrar no
  `enum` do schema da OpenAI).
