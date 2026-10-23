# examssh

MVP em Python para praticar o fluxo ExamShell/Grademe do Exam Rank 02. A sessão acontece em um container acessado por SSH. Um repositório Git contém `subjects/` e `rendu/`: o candidato lê os enunciados, envia a solução e chama `grademe` para avaliar o push.

O conteúdo usa exercícios conhecidos do Exam Rank 02, com enunciados próprios e resumidos. Este projeto não é oficial nem afiliado à 42.

## Requisitos

- Docker Desktop com Docker Compose v2.
- Cliente SSH e Git no computador.

## Iniciar

Na pasta do projeto:

```powershell
docker compose up --build -d
ssh -p 2222 exam@127.0.0.1
```

Na primeira conexão, confirme a chave de host. Use a conta SSH `exam` e a senha local padrão `exam`. Para mudar a senha SSH, defina `EXAM_PASSWORD` antes de iniciar o Compose. Com a API configurada, o ExamShell pede as credenciais do app; sem API, pede um dos logins locais `trial` ou `normal`. Por padrão, as portas ficam limitadas ao loopback local.

## Integração com a API da trilha

O Compose usa por padrão a API local em `http://host.docker.internal:8100`. Para apontar a outra instância, defina `TRILHA_API_URL` no `.env`; em produção, use a URL pública do app. Opcionalmente, configure `TRILHA_API_TIMEOUT` (segundos, padrão `10`) e `TRILHA_SOURCE` (padrão `examshell`). Para desativar a integração e usar os perfis locais `trial` e `normal`, defina `TRILHA_API_URL=` no `.env`.

No modo API, o usuário digita suas credenciais do app ao conectar por SSH. O ExamShell consulta `/api/path/next`, mostra atividades de código quando houver `examshell_id` e direciona as demais ao site. Para uma atividade de código, o repositório exibido contém o enunciado em `subjects/subject/<slug>/subject.en.md` e recebe a solução em `rendu/<slug>/<arquivo>`. Depois de fazer push de um commit novo que altere o arquivo esperado, `grademe` executa a bateria de testes, envia `activity_id`, `correct` (`true`/`false`) e `source` para `/api/activity/complete`, e carrega a próxima atividade. O progresso e a regra de reforço permanecem sob controle do app.

### Modos locais `trial` e `normal`

Esses perfis ficam disponíveis quando `TRILHA_API_URL` está vazio. O login `trial` percorre as cinco questões uma vez: cada submissão que contém o arquivo da questão consome a questão, mesmo se compilação ou testes falharem. O login `normal` mantém a questão atual até a solução passar; após uma falha, faça uma nova alteração, commit e push antes de tentar novamente. Os logins mantêm progresso separado.

### Acesso por outro dispositivo na mesma rede

No arquivo `.env`, defina o IPv4 da máquina que está rodando Docker (no Windows, veja `ipconfig`; no Linux, `ip a`):

```env
EXAMSHELL_HOST_IP=192.168.1.20
```

Substitua o exemplo pelo endereço da máquina e reinicie com `docker compose up --build -d`. No outro dispositivo, conecte usando `ssh -p 2222 exam@192.168.1.20`. O link Git mostrado pelo ExamShell também usa esse IP. Os dispositivos precisam estar na mesma rede, e o firewall da máquina deve permitir as portas TCP `2222` e `9418`.

Em um terminal normal da sua máquina (fora da conexão SSH), clone uma vez o URL Git apresentado pelo ExamShell:

```sh
git clone git://localhost:9418/trial.git
cd trial
```

O endereço `trial.git` é o exemplo para o login trial. Para o login normal, use o endereço `normal.git` mostrado na tela e entre na pasta `normal`.

O repositório contém as pastas `subjects/` e `rendu/`. Leia o enunciado em `subjects/<exercicio>/subject.en.md`. Crie o arquivo C no caminho de submissão indicado pelo `examshell` e envie:

```sh
mkdir -p rendu/ft_strlen
# crie rendu/ft_strlen/ft_strlen.c
git add rendu/ft_strlen
git commit -m "solve ft_strlen"
git push origin master
```

Volte à conexão SSH, que está no prompt `examshell>`, e execute `grademe`. Ele pergunta `Verify that you made git push. Do you want to continue? [Y/N]`. Responda `Y` para o avaliador clonar o repositório em um diretório temporário e testar o último push. No modo `trial`, uma falha marca a questão errada e avança; no modo `normal`, a questão permanece aberta até passar. Cada login recebe um repositório Git próprio, mas ambos usam as mesmas cinco questões enquanto os bancos de questão forem locais. Quando avançar, o ExamShell publica o próximo enunciado em `subjects/<exercicio>/subject.en.md`; atualize o clone local com `git pull --rebase`. O prompt ExamShell aceita `grademe`, `status`, `finish`, `help` e `exit`.

## Questões incluídas

`ft_strlen`, `ft_swap`, `first_word`, `last_word` e `wdmatch`, nessa ordem.

## Parar e apagar os dados

```powershell
docker compose down
```

As submissões e sessões ficam no volume Docker `exam-data` e sobrevivem a esse comando. Para apagar esse volume e os dados locais da prática:

```powershell
docker compose down --volumes
```

## Limites deste MVP

Os logins locais `trial` e `normal` são perfis de teste, sem senha de aplicação. No modo API, autenticação é feita pelas credenciais do app. O serviço usa senha SSH de desenvolvimento (`exam` por padrão) e Git daemon sem autenticação. Os repositórios ficam separados por usuário para isolar o fluxo de avaliação, mas isso não é autenticação de produção: não exponha o container na internet nem use para avaliar código de pessoas não confiáveis. O avaliador aplica limites básicos de tempo, memória e tamanho de arquivo, mas ainda executa C no mesmo container. Para hospedagem multiusuário, será necessário autenticar o Git e isolar melhor o worker de avaliação.
