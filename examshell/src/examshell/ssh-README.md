# ExamShell Rank 02 — ambiente local de prática

Esta conexão SSH já é o ExamShell. A conta SSH é `exam` (senha local padrão `exam`). Depois da conexão, informe o login de aplicação `trial` ou `normal`; ainda não há senha para esses logins.

## Como funciona

- O prompt `examshell>` aceita `grademe`, `status`, `finish`, `help` e `exit`.
- Os enunciados e suas soluções ficam no repositório Git do login, organizado nas pastas `subjects/` e `rendu/`.
- O clone e a edição acontecem no terminal normal da sua máquina, fora desta conexão SSH.
- O comando `grademe` pergunta se você já fez `git push`. Responda `Y` para confirmar. O avaliador clona o repositório, testa a solução e retorna o resultado.
- No login `trial`, cada push com o arquivo da questão consome a questão, mesmo com erro de compilação ou teste. No login `normal`, uma falha mantém a mesma questão aberta; faça um novo commit e push para tentar de novo.
- Os dois logins mantêm progresso separado. Ambos usam por enquanto as mesmas cinco questões Rank 02.
- Quando o exame avança, o ExamShell publica o próximo enunciado no mesmo repositório e apresenta a questão seguinte.

## Preparar o repositório na sua máquina

Copie o URL mostrado abaixo e execute no terminal normal do computador:

```sh
git clone git://localhost:9418/trial.git
cd trial
```

O link mostrado pelo ExamShell é específico do login: termina em `trial.git` ou `normal.git`. Na pasta clonada, leia `subjects/<exercicio>/subject.en.md` e crie a solução no caminho `rendu/<exercicio>/` indicado pelo ExamShell. Depois faça commit e push:

```sh
git add rendu/<exercicio>
git commit -m "solve <exercicio>"
git push origin master
```

Volte a esta conexão SSH e digite `grademe`. Se a questão passar, atualize o clone na sua máquina antes de começar a próxima:

```sh
git pull --rebase
```

Este simulador é um projeto independente, não oficial da 42. Use somente no ambiente local de prática fornecido pelo Docker Compose.
