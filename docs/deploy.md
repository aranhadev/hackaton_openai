# Deploy — Trilha C na droplet da DigitalOcean

Destino: droplet **`tester-hackathon`** (1 GB, NY1), já cadastrada no **Resource Manager** do Wappler.
Quem cria o target e clica em Deploy é a Dani, pela IDE. Este guia diz o que marcar e como conferir.

> Os nomes de menus abaixo seguem o Wappler 6. Se algum rótulo estiver diferente na sua versão,
> o campo é o mesmo: procure pelo nome da opção.

## 0. Antes de começar

- [ ] No **Resource Manager**, a droplet `tester-hackathon` precisa estar **ativa e acessível**.
  Hoje ela aparece como `status: new` e `access: false`. Abra o item e deixe o Wappler terminar o
  provisionamento: ele instala o Docker e cadastra a chave SSH. Só siga quando ela aparecer conectada.
- [ ] Mudanças salvas e servidor de Development funcionando (`http://localhost:8100`).
- [ ] Ter em mãos: a chave da OpenAI (`OPENAI_API_KEY`), um domínio apontando para o IP da droplet
  (opcional, para HTTPS) e uma **senha nova** para o Postgres de produção. Não reaproveite a do Development.

## 1. Criar o target Production

*Project Settings → Targets → + (New Target)*

| Campo | Valor |
|---|---|
| Name | `Production` |
| Target Type | **Docker** |
| Docker Machine / Host | `tester-hackathon` (do Resource Manager) |
| Web Server | Node.js · Node Version **lts** · Node OS **alpine** (igual ao Development) |
| Image Type | **slim** (igual ao Development) |
| Web Server Port | `80`, ou deixe o Wappler usar o proxy com SSL (abaixo) |
| Timezone | `America/Sao_Paulo` |
| Database | **PostgreSQL 17.2.x** (igual ao Development) |
| Database user / password / name | `db_user` / *senha nova* / `hacktonopenaitrilha4` |
| Sample data | **desmarcado** (os dados vêm dos seeds) |
| Logging | max files `5`, max size `10m` |

Com domínio, ative o **SSL / Let's Encrypt (Traefik)** do target e informe o domínio e um e-mail.
Com HTTPS, o login por cookie funciona de forma mais previsível.

**Sobre o argon2 no build:** o pacote `argon2@0.40.3` do `package.json` traz binários prontos
para `linux-x64` nas variantes **musl** (alpine) e **glibc** (slim/debian). Conferido no container
de Development: Alpine, x86_64, Node v24, `hash` + `verify` funcionam e **nada é compilado** no
`npm install`. O target de produção só precisa ter o que o Development já tem:
- arquitetura **x86_64**: as droplets comuns da DigitalOcean são x86_64. Uma droplet ARM também tem prebuild (`linux-arm64`);
- Node **lts** e o `npm install` **sem** `--ignore-scripts`. É o padrão do Dockerfile que o Wappler gera;
- `argon2` em `dependencies` (já está).

## 2. Variáveis de ambiente do target

Com o target **Production** ativo: *Server Connect Settings → Environment* (fica no
`app/config/config.json` do target, que está no `.gitignore`).

| Variável | Valor em produção | Quem lê |
|---|---|---|
| `OPENAI_API_KEY` | chave da OpenAI | `diagnostic/finish` (explicação da trilha) |
| `OPENAI_MODEL` | `gpt-4.1-mini` (o mesmo do Development) | `diagnostic/finish` |
| `DEMO_RESET_ENABLED` | `true` **só durante a demo**; `false` depois | `demo/reset` |
| `DEMO_RESET_TOKEN` | segredo longo e aleatório, **diferente** do Development (ex.: `openssl rand -base64 24`) | `demo/reset`: só reseta com `token` igual a este valor. Vazio = reset sempre recusado |

E, nas configurações do servidor:

| Config | Valor | Observação |
|---|---|---|
| `secret` (Server Connect Settings) ou env `WAPPLER_SERVER_SECRET` | texto aleatório novo, 32+ caracteres | Assina o cookie de sessão. **Não** reaproveite o do Development |
| `debug` | `false` | Já está `false` |

Sem `OPENAI_API_KEY`, o `finish` continua funcionando e usa o texto padrão (Try/Catch).

## 3. Primeiro deploy

1. Selecione o target **Production** na barra de baixo (*Target: Production*).
2. Clique em **Deploy**. O Wappler gera o `docker-compose.yml` e o `Dockerfile` do target, envia
   para a droplet e sobe `web` + `db`.
3. Acompanhe o *Output*. O `npm install` precisa de acesso ao `registry.npmjs.org`. Da droplet ele
   funciona; a falha de rede de hoje era da sua rede local.
4. Em 1 GB, Postgres + Node cabem para a demo. Se o build travar por memória, crie um swap de 1 GB
   na droplet ou suba temporariamente para 2 GB.

## 4. Banco: migrations e seeds

Com o target **Production** ativo:

1. *Database Manager → db → Changes →* refresh → **Apply** em todas. São 9 migrations, de
   `20261023163431_user, learning path` até `20261023220000_user hash argon2` (a última recusa
   qualquer senha que não seja hash argon2).
2. *Database Manager → Seeds →* rode **`diagnostico_demo`** e depois **`trilha_pratica`**, nessa ordem.
3. Confira em *Database Manager → db*: as tabelas `skill`, `question`, `activity` e `user`, e as views
   `attempt_skill_score`, `user_skill_score` e `attempt_path_plan`.

**Teste de banco do zero (feito em 23/10):** num banco descartável novo (`hackton_deploytest`,
já apagado), as 8 migrations + os 2 seeds recriaram tudo:

| Item | Resultado |
|---|---|
| Habilidades | 3 (`ponteiros` 1, `memoria` 2, `algoritmos` 3 em `sort_order`) |
| Questões diagnósticas | 5 |
| Questões de prática | 9 |
| Alternativas | 56 |
| Atividades | 9 |
| Usuários | `ana`, `bruno` |
| Views | `attempt_path_plan`, `attempt_skill_score`, `user_skill_score` |

Rodar os seeds **duas vezes** não duplicou nada: eles são idempotentes.

O que os seeds **não** fazem:
- Não criam tentativas nem trilhas para Ana e Bruno. A trilha nasce quando eles fazem o diagnóstico na demo (ou pelo `demo/reset`).
- Não preenchem `activity.examshell_id` (ver `docs/contrato-examshell.md`).
- Senha nunca vai em texto puro: o seed grava só o **hash argon2id** de Ana e Bruno, e a migration
  `user hash argon2` (check `hash like '$argon2%'`) faz o banco recusar qualquer outra coisa.
  A senha da demo continua conhecida (está no roteiro); depois do hackathon, troque ou apague os dois.

## 5. Reset da demo

Com `DEMO_RESET_ENABLED=true` e o token configurado:

```bash
curl -X POST --data-urlencode "token=$DEMO_RESET_TOKEN" https://SEU_DOMINIO/api/demo/reset
```

Sem `DEMO_RESET_ENABLED=true`, sem `DEMO_RESET_TOKEN` no servidor ou com token errado, a resposta é
`403 {"error":"Reset da demo desabilitado ou token inválido …"}`. Não coloque o token em URL
(query string): mande no corpo do POST, como acima.

## 6. Smoke test

Troque `BASE` pela URL do app (`https://SEU_DOMINIO` ou `http://IP_DA_DROPLET`).

```bash
BASE=https://SEU_DOMINIO
```

```bash
curl -s -o /dev/null -w "home %{http_code}\n" $BASE/
```

```bash
curl -s -c ck.txt -w "\nlogin %{http_code}\n" -d "username=ana&password=demo123" $BASE/api/auth/login
```

```bash
curl -s -b ck.txt -w "\nstart %{http_code}\n" -X POST $BASE/api/diagnostic/start
```

```bash
curl -s -b ck.txt -w "\ncurrent %{http_code}\n" $BASE/api/path/current
```

```bash
curl -s -b ck.txt -w "\nreport %{http_code}\n" $BASE/api/progress/report
```

```bash
curl -s -o /dev/null -w "sem login %{http_code}\n" $BASE/api/path/current
```

Esperado:

| Chamada | Status | Corpo |
|---|---|---|
| home | 200 | página inicial |
| login | 200 | `{"identity": <id da Ana>}` |
| start | 200 | `attempt_id` da nova tentativa |
| current | 200 | `query_path` vazio (Ana ainda sem trilha) ou a trilha dela |
| report | 200 ou 404 | 404 `Nenhuma trilha ativa` é **normal** antes do primeiro diagnóstico |
| sem login | 401 | `Unauthorized` |

Depois, faça o fluxo completo no navegador: `/diagnostico` com a Ana (errando as duas de
ponteiros) → `/trilha` deve mostrar **P1 → P2 → P3 → M3 → A3**. Repita com o Bruno (errando a
3ª e a 5ª) → **A1 → A2 → A3 → M2 → M3 → P3**. Isso confirma a OpenAI, as views e a regra da trilha
em produção.

Pela IDE, a lista de páginas que deve responder 200: `/`, `/diagnostico`, `/trilha`, `/progresso`
(e `/design`, o catálogo visual).

## 7. Depois do deploy

- [ ] `DEMO_RESET_ENABLED=false` quando a apresentação acabar (e apague o `DEMO_RESET_TOKEN`).
- [ ] **Chave da API da DigitalOcean:** ela está no `.wappler/project.json`, que já está no
  commit `f1da09b`. O repositório não tem remote hoje. Antes de qualquer `git push`, **gere uma
  chave nova** no painel da DigitalOcean (*API → Tokens*), atualize o Resource Manager e revogue a antiga.
- [ ] ExamShell: não exponha publicamente sem senha forte e firewall (ver `docs/contrato-examshell.md`).
