# Plano do projeto: ExamShell Rank 02

## Objetivo

Construir em Python um simulador local do fluxo do ExamShell/Grademe usado para praticar o Exam Rank 02 da 42. O candidato entra por SSH, informa seu login, recebe o exercício atual e envia a solução pelo Git. Ao executar `grademe`, o sistema valida a revisão enviada e aplica a progressão definida pelo modo do perfil.

O simulador reproduz o fluxo de estudo; não é um serviço oficial da 42 nem integra com a Moulinette. O acesso atual usa dois logins locais de teste (`trial` e `normal`); futuramente, perfis, exames e testes serão carregados de uma API externa.

## Escopo inicial (MVP)

- Uma sessão SSH em container, com Python e Git instalados.
- Na entrada, mostrar somente o `README.md` de boas-vindas e o prompt de shell.
- Depois da conexão SSH, pedir um login de aplicação. `trial` consome cada questão submetida; `normal` exige aprovação para avançar. Cada login mantém estado e repositório Git próprios.
- A conexão SSH inicia diretamente o prompt ExamShell, imprime o guia e mostra exercício/URL; não é necessário executar `examshell` manualmente.
- Comando `grademe` pergunta se o candidato já fez `git push`; após confirmação, clona o repositório em diretório temporário e avalia o último envio.
- Um exame fixo de cinco exercícios do conjunto público de Exam Rank 02, em progressão de dificuldade:
  1. `ft_strlen` — Level 1
  2. `ft_swap` — Level 1
  3. `first_word` — Level 1
  4. `last_word` — Level 2
  5. `wdmatch` — Level 2
- Os exercícios pedem implementações em C, para manter a prática alinhada ao exame; Python será usado para construir o simulador e o avaliador.
- `finish` encerra a sessão e exibe o resultado final.

Os nomes e níveis acima aparecem em repositórios públicos de preparação para o Exam Rank 02. Os enunciados do MVP serão mantidos em arquivos próprios e concisos, descrevendo requisitos e exemplos sem copiar soluções de terceiros.

## Fluxo do candidato

1. Conectar por SSH ao container com a conta de prática. O SSH força a entrada no prompt ExamShell e imprime o guia inicial.
2. No terminal normal da máquina do candidato, clonar uma vez o URL Git mostrado pelo ExamShell e trabalhar em `rendu/<nome>/`. Consultar o enunciado em `subjects/<nome>/subject.en.md`.
3. Fazer `git add`, `git commit` e `git push` para esse mesmo repositório na máquina local.
4. Voltar à conexão SSH e executar `grademe`. Após confirmação, o avaliador clona o último push em diretório temporário, compila/executa os testes e informa aprovação ou erros.
5. No modo `trial`, uma submissão com arquivo presente consome a questão, mesmo reprovada. No modo `normal`, uma reprovação mantém a questão atual até uma aprovação.
6. Quando o modo avança, o sistema adiciona o próximo enunciado em `subjects/<nome>/`, faz commit e push no repositório do login e anuncia a questão seguinte. O candidato executa `git pull --rebase`.
7. Após avaliar as cinco questões, informar o resultado; `finish` encerra a tentativa.

## Organização dos repositórios Git

O servidor cria um repositório bare limpo por login (`trial.git` e `normal.git`), iniciado com o primeiro enunciado e `rendu/` vazio. Na raiz de cada um ficam `subjects/<exercicio>/subject.en.md` e `rendu/<exercicio>/<arquivo>`. Quando o modo avança, o ExamShell clona o repositório daquele login em área temporária, adiciona o próximo enunciado em `subjects/<exercicio>/`, faz commit e push de volta.

## Arquitetura proposta

- **`examshell` (Python CLI):** máquina de estados e prompt interativo para comandos do exame; persistência do estado da tentativa.
- **Perfis e modos:** consulta local dos logins de teste e política de avanço. A camada `profiles.py` é o ponto de integração futuro para buscar usuários, modos e bancos de questões na API.
- **Catálogo de questões:** configuração declarativa local com identificador, nível, caminho do enunciado, arquivos esperados, comando de compilação e suíte de testes; futuramente, entregue pela API.
- **Grademe:** pede confirmação do push, clona o repositório do login em diretório temporário, compila e executa testes com limites básicos; a política do modo determina se uma reprovação avança ou permite retry.
- **Servidor Git:** repositórios bare limpos separados por login, servidos por Git daemon no ambiente local; cada raiz contém `subjects/` e `rendu/`.
- **Container SSH:** imagem Docker com usuário de desenvolvimento, senha local, Python, Git e cliente C. O SSH força o comando ExamShell; o mesmo container executa o Git daemon e persiste os dados necessários.
- **Testes das questões:** casos do enunciado mais casos de borda, mantidos no código do avaliador. Este MVP local não trata os casos como segredo contra o usuário do container.

## Estrutura de arquivos prevista

```text
src/examshell/          # CLI, sessão, catálogo e avaliador
subjects/<id>/          # subject.en.md do enunciado
deploy/                 # Dockerfile, configuração SSH e provisionamento Git
tests/                  # testes do simulador, Git e transições de sessão
README.md               # instalação e uso pelo mantenedor
PROJECT_PLAN.md         # este planejamento
```

Cada repositório de login é iniciado a partir do primeiro enunciado empacotado. Cada avanço publica o próximo `subjects/<id>/subject.en.md` no histórico do login, junto às submissões em `rendu/`.

## Fases de implementação

1. **Contrato do MVP:** fechar fluxo, comandos, nomes das pastas e critérios de aprovação; registrar casos de teste das cinco questões.
2. **CLI e sessão:** implementar `examshell`, estado persistente, apresentação de questão, `status` e `finish`.
3. **Git local:** criar um repositório limpo com `subjects/` e `rendu/` para cada login; identificar commits enviados para a questão corrente.
4. **Grademe:** pedir confirmação, clonar o repositório enviado, testar em subprocesso com limites e publicar o próximo subject somente após aprovação.
5. **SSH e Docker Compose:** empacotar ambiente, README de entrada, usuário sem privilégios e instruções para os dois terminais.
6. **Validação ponta a ponta:** simular conexão SSH, clone, submissão aprovada, submissão reprovada, retry, progressão e conclusão.

## Estado do projeto

O MVP contém o container SSH, os logins locais `trial` e `normal`, progresso e repositório Git separados por login, confirmação interativa do `grademe`, avaliação por clone temporário e política de avanço por modo. A configuração de perfis/modes fica isolada para futura integração com API externa. A validação ponta a ponta ainda precisa ser feita em um host com Docker Compose.

## Critérios de aceite

- Uma pessoa consegue entrar por SSH e entender o fluxo apenas pelo README inicial.
- `examshell` apresenta questão atual e URLs Git válidas no ambiente iniciado.
- Uma submissão sem `git push` não é avaliada como nova.
- `grademe` avalia o commit enviado e aplica a política do login: trial avança em sucesso ou falha; normal só avança em sucesso.
- Os dois logins mantêm sessões e repositórios isolados; ao avaliar cinco questões, a sessão termina corretamente.
- A avaliação compila e executa em diretório temporário, com limites básicos de CPU, memória, tempo e tamanho de arquivo. Os casos ficam no código do MVP local e não devem ser tratados como segredo contra o próprio usuário do container.
- O ambiente pode ser inicializado e reiniciado de forma reproduzível por Docker Compose.

## Decisões e riscos em aberto

- **Isolamento do código submetido:** Docker sozinho não basta se o container de avaliação compartilhar permissões excessivas. Antes de aceitar código de terceiros, usar usuário sem privilégios, filesystem temporário, limites de CPU/memória/tempo e rede desativada no processo de teste.
- **Acesso Git:** para o MVP local, usar chaves por usuário ou credenciais de desenvolvimento documentadas; não reutilizar credenciais pessoais.
- **Persistência:** guardar estado da tentativa fora do container efêmero, associado ao usuário SSH e aos commits avaliados.
- **Autenticidade dos exercícios:** os cinco nomes são candidatos do Exam Rank 02; os requisitos funcionais devem ser revistos contra enunciados autorizados/disponíveis antes da implementação dos testes.
- **Modelo de uso:** os logins `trial` e `normal` são contas de demonstração sem senha de aplicação, em prática local com Docker Compose. A integração com API e autenticação real fica para uma fase futura.

## Referências consultadas

- [Lista pública de exercícios por nível do Exam Rank 02](https://github.com/alexhiguera/Exam_Rank_02_42_School) — referência comunitária para nomes e níveis.
- [Exemplo público de fluxo ExamShell/Grademe e diretórios subject/Rendu](https://github.com/42-Yerevan-Armenia/Exam_Rank_02) — referência comunitária para o fluxo de comandos e submissão Git.

