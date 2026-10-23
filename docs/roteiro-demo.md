# Roteiro da demo (~3 min)

Mostra que **o mesmo diagnóstico gera trilhas diferentes** para dois alunos, que a trilha reage
quando o aluno erra uma prática e que a IA só explica o resultado. Fontes:
[spec-diagnostico.md](spec-diagnostico.md), [spec-trilha.md](spec-trilha.md),
[contrato-trilha.md](contrato-trilha.md) e os seeds `.wappler/seeds/db/diagnostico_demo.js` e
`trilha_pratica.js`.

| Persona | Login | Erra no diagnóstico | Trilha esperada |
|---|---|---|---|
| Ana | `ana` / `demo123` | Q1 e Q2 (ponteiros) | P1 → P2 → P3 → M3 → A3 |
| Bruno | `bruno` / `demo123` | Q3 (memória) e Q5 (algoritmos) | A1 → A2 → A3 → M2 → M3 → P3 |

| Bloco | Tempo |
|---|---|
| 1. Abertura | 0:00–0:15 |
| 2. Ana faz o diagnóstico | 0:15–0:55 |
| 3. Resultado da Ana | 0:55–1:25 |
| 4. Bruno faz o diagnóstico | 1:25–2:05 |
| 5. Bruno na trilha: erro e reforço | 2:05–2:40 |
| 6. Fechamento | 2:40–3:00 |

## Antes de subir no palco (checklist)

- [ ] Target **Development** rodando no Wappler → `http://localhost:8100` abre.
- [ ] Migrations aplicadas e seeds rodados, nesta ordem: `diagnostico_demo` (5 questões,
      9 atividades, Ana e Bruno) e `trilha_pratica` (1 questão de prática por atividade).
- [ ] Variáveis de ambiente: `OPENAI_API_KEY`, `OPENAI_MODEL = gpt-4.1-mini`, `DEMO_RESET_ENABLED = true` e `DEMO_RESET_TOKEN` (segredo; fica só no Wappler e no seu terminal).
- [ ] Botão **Sair** e página **/progresso** no ar (feitos em outra sessão; conferir no ensaio).
- [ ] **Reset** (abaixo) feito há pouco e ninguém logado.
- [ ] DevTools → aba **Network** aberta (para mostrar o JSON do `finish`, se perguntarem).
- [ ] Ensaio completo feito uma vez e a resposta do `finish` veio com `explanation_source = "openai"`.

## 0. Reset (antes de começar, fora do tempo)

Apaga tentativas, trilhas e progresso **só** de `ana` e `bruno` (questões e atividades ficam):

```bash
curl -X POST --data-urlencode "token=$DEMO_RESET_TOKEN" http://localhost:8100/api/demo/reset
```

(Antes, no terminal: `export DEMO_RESET_TOKEN=...` com o valor do Wappler; no servidor, troque a URL.)
Resposta: `{"reset":[{"attempts":…,"paths":…,"progress":…}]}`. Se vier **403**, falta
`DEMO_RESET_ENABLED=true`, falta o `DEMO_RESET_TOKEN` no target ou o token está errado.

## 1. Abertura — tela inicial `/` (≈15 s)

**Falar:** "Todo curso de C começa igual para todo mundo. Mas quem trava em ponteiros e quem
trava em algoritmos precisam de caminhos diferentes. A gente faz 5 questões e monta a trilha
a partir dos erros."

Clicar em **Começar diagnóstico**.

## 2. Ana faz o diagnóstico — `/diagnostico` (≈40 s)

1. Login `ana` / `demo123` → **Entrar e começar**.
2. Responder as 5 questões (a barra mostra "x de 5"):
   - **Q1** (`*p` com `int *p = &x`): escolher **"O endereço de memória de x"** (errada).
   - **Q2** (`p++` em vetor): escolher **"4"** (errada).
   - **Q3, Q4, Q5**: responder a correta (comportamento indefinido · `free(s); s = NULL;` · lê `v[n]`).
3. **Finalizar**.

**Falar enquanto responde:** "Cada alternativa errada foi escrita para revelar uma confusão
específica — aqui, confundir o endereço com o valor. O servidor corrige; o gabarito nunca vai
para o navegador."

## 3. Resultado da Ana — "Sua trilha está pronta" (≈30 s)

Apontar, de cima para baixo:

- **Resumo e por que começa aqui** (texto da IA).
- **O que seus erros mostram**: uma confusão por erro, comparando a alternativa escolhida com a correta.
- **Suas habilidades**: ponteiros 0 %, memória e algoritmos 100 %.
- **Sua trilha**: **P1 → P2 → P3 → M3 → A3**.

**Falar:** "Quem montou a trilha não foi a IA. É uma regra fixa no banco: acerto abaixo de 50 %
começa no nível 1, abaixo de 100 % no nível 2, 100 % só o nível 3, e a habilidade mais fraca vem
primeiro. A IA recebe a trilha pronta e só explica — num JSON validado por schema, então a tela
nunca quebra."

Clicar em **Sair**.

## 4. Bruno faz o diagnóstico (≈40 s)

1. Em `/diagnostico`, **Começar** → aparece o login → `bruno` / `demo123`.
2. Responder:
   - **Q1, Q2**: corretas (`10` · `2`).
   - **Q3** (função devolve `&x`): escolher **"Sempre lê 5"** (errada).
   - **Q4**: correta (`free(s); s = NULL;`).
   - **Q5** (laço `i <= n`): escolher **"Nenhum, o laço está correto"** (errada).
3. **Finalizar** e mostrar a trilha: **A1 → A2 → A3 → M2 → M3 → P3**.

**Falar:** "Mesmas 5 questões. Ana começou em ponteiros do zero; Bruno começa em algoritmos e
entra em memória já no nível 2. Ponteiros, que ele domina, fica só o desafio final."

Clicar em **Começar a trilha**.

## 5. Bruno na trilha: erro e reforço — `/trilha` (≈35 s)

1. **A1** (corpo do `for` com `n = 0`): escolher **"Nenhuma"** → **Responder** → "Acertou" e
   a trilha avança para A2.
2. **A2** (condição de parada da `strlen`): escolher **"`while (s[i] != NULL) i++;`"** (errada) →
   **Responder**. Aparece "Não foi dessa vez", a confusão (`'\0'` × `NULL`) e
   **"Antes de tentar de novo, faça o reforço: A1 · Laços e limites de vetor"**. O passo atual
   volta para A1.
3. **A1** de novo: **"Nenhuma"** → **Responder**.
4. **A2**: escolher **"`while (s[i] != '\0') i++;`"** → **Responder** → "Acertou" e avança para A3.

**Falar:** "A correção da prática também é no servidor. Errou, a trilha manda revisar o nível
anterior da mesma habilidade antes de tentar de novo. Se o reforço ainda não estivesse na trilha,
ele seria inserido antes da atividade errada."

## 6. Fechamento — `/progresso` (≈20 s)

Abrir **Progresso** no menu: o avanço do Bruno por habilidade.

**Falar:** "A trilha fica gravada com o motivo de cada passo, e o progresso sai por API. As
mesmas APIs — `path/next`, `activity/complete` e `progress/report` — são o que o ExamShell, em
Python, consome para corrigir código de verdade e devolver o resultado para a trilha."

Se a `/progresso` não estiver pronta, mostrar no terminal (com a sessão do Bruno):

```bash
curl -c ck.txt -d "username=bruno&password=demo123" http://localhost:8100/api/auth/login
```

```bash
curl -b ck.txt http://localhost:8100/api/progress/report
```

## Se a OpenAI falhar

O `diagnostic/finish` chama a OpenAI dentro de um **Try/Catch**. Chave inválida, cota, modelo
errado, timeout (20 s), resposta cortada ou recusada → cai no Catch, que monta a explicação
**com os dados do banco** (o `feedback` de cada alternativa errada), **no mesmo formato do schema**.
A resposta continua 200 e a tela é a mesma; só muda `explanation_source` de `"openai"` para
`"fallback"`. A trilha, a prática e o reforço não dependem da OpenAI.

O que fazer:

- **Não parar a demo.** A trilha, as habilidades e as confusões aparecem do mesmo jeito.
- Os textos ficam mais secos: o resumo vira "Sua trilha começa por ponteiros, a habilidade em
  que você teve o menor acerto no diagnóstico." e o primeiro foco vira o título da atividade.
- **Transformar em argumento:** "Se a IA cair, o aluno não fica sem resposta: a regra e o
  feedback das alternativas estão no banco. A IA melhora o texto, não sustenta o sistema."
- Se perguntarem, mostrar na aba Network a resposta do `finish` com `"explanation_source": "fallback"`.
- "Montando sua trilha…" pode demorar até 20 s antes do fallback (timeout da chamada). Preencher
  falando da regra da trilha.

Outros imprevistos:

| Sintoma | Causa provável | Ação |
|---|---|---|
| Pede login de novo no meio | sessão expirou | logar de novo e continuar |
| Trilha diferente da esperada | alternativa errada clicada no diagnóstico | **Refazer diagnóstico** (cria outra tentativa e outra trilha) |
| Prática sem alternativas ("Marcar como concluída") | seed `trilha_pratica` não rodou | rodar o seed; na hora, clicar e seguir |
| Reset responde 403 | `DEMO_RESET_ENABLED`/`DEMO_RESET_TOKEN` não definidas, ou token errado | definir as duas, reiniciar o target e conferir o token do curl |
| "Não deu para montar sua trilha" | faltam atividades no banco | rodar o seed `diagnostico_demo` |
