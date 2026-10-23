// Seed das questões de prática da trilha (linguagem C).
// Requer o seed "diagnostico_demo" (as 9 atividades P1..A3) e a migration "trilha personalizada".
// Cria 1 questão por atividade (kind = 'practice') com 4 alternativas e feedback nas erradas.
// Ligação com a atividade: question.source_ref = 'activity:<activity.id>' (sem coluna nova).
// Idempotente: pula a atividade que já tem questão com esse source_ref.
// O activity/complete corrige no servidor pelo option_id; errou -> reforço do nível anterior.

const practice = [
  {
    activity: 'P1', correctAt: 3,
    statement: 'Depois de `int x = 42; int *p = &x; *p = 7;`, quanto vale `x`?',
    explanation: '`*p = 7` escreve no endereço guardado em `p`, que é o de `x`. Então `x` passa a valer 7.',
    options: [
      { text: '7', correct: true },
      { text: '42', feedback: 'Acha que `*p = 7` muda só o ponteiro, não a variável apontada.' },
      { text: 'O endereço de x', feedback: 'Confunde `*p` (o valor no endereço) com `p` (o endereço).' },
      { text: 'Erro: não dá para atribuir através de ponteiro', feedback: 'Acha que `*` só lê; ele também escreve no endereço apontado.' }
    ]
  },
  {
    activity: 'P2', correctAt: 1,
    statement: 'Com `int v[5] = {10, 20, 30, 40, 50}; int *p = v + 1;`, o que `*(p + 2)` vale?',
    explanation: '`p` aponta para `v[1]`; `p + 2` aponta para `v[3]`, que vale 40.',
    options: [
      { text: '40', correct: true },
      { text: '30', feedback: 'Esquece que `p` já começa em `v[1]`, não em `v[0]`.' },
      { text: '22', feedback: 'Soma 2 ao valor apontado em vez de avançar 2 elementos.' },
      { text: '20 + 2 bytes, valor indefinido', feedback: 'Acha que aritmética de ponteiros soma bytes, não elementos.' }
    ]
  },
  {
    activity: 'P3', correctAt: 4,
    statement: 'Para uma função mudar para onde o ponteiro `int *p` do chamador aponta, qual assinatura e chamada usar?',
    explanation: 'Para alterar um ponteiro dentro da função, passe o endereço dele: `void f(int **pp)` e `f(&p)`.',
    options: [
      { text: '`void f(int **pp)` chamada com `f(&p)`', correct: true },
      { text: '`void f(int *pp)` chamada com `f(p)`', feedback: 'Passa uma cópia do ponteiro: a função muda só a cópia.' },
      { text: '`void f(int **pp)` chamada com `f(p)`', feedback: 'Confunde o ponteiro com o endereço do ponteiro na chamada.' },
      { text: '`void f(int &pp)` chamada com `f(p)`', feedback: 'Mistura C com C++: referência (`&` na assinatura) não existe em C.' }
    ]
  },
  {
    activity: 'M1', correctAt: 2,
    statement: 'Qual versão de `int *f(void)` devolve um ponteiro que continua válido depois que `f` retorna?',
    explanation: 'Memória do `malloc` fica na heap e vive até o `free`; a variável local morre quando a função retorna.',
    options: [
      { text: '`int *x = malloc(sizeof *x); *x = 5; return x;`', correct: true },
      { text: '`int x = 5; return &x;`', feedback: 'Não distingue o tempo de vida da stack (local) do da heap.' },
      { text: '`int x = 5; int *p = &x; return p;`', feedback: 'Guardar o endereço em outro ponteiro não muda o tempo de vida de `x`.' },
      { text: '`int *x; *x = 5; return x;`', feedback: 'Usa um ponteiro não inicializado: ele não aponta para memória válida.' }
    ]
  },
  {
    activity: 'M2', correctAt: 4,
    statement: '`int *v = malloc(n * sizeof(int));` Qual sequência evita vazamento e erro se faltar memória?',
    explanation: 'Teste se o retorno é NULL antes de usar e chame `free(v)` exatamente uma vez no fim.',
    options: [
      { text: 'Testar `if (!v)` antes de usar e chamar `free(v)` uma vez no fim', correct: true },
      { text: 'Usar `v` direto e chamar `free(v)` duas vezes por segurança', feedback: 'Acha que `free` duplo é inofensivo; é comportamento indefinido.' },
      { text: 'Não chamar `free`: o sistema libera quando a função termina', feedback: 'Confunde heap (liberação manual) com stack (liberação automática).' },
      { text: 'Chamar `free(*v)` no fim', feedback: 'Confunde o ponteiro com o valor apontado na hora de liberar.' }
    ]
  },
  {
    activity: 'M3', correctAt: 1,
    statement: 'Qual é o jeito seguro de dobrar um vetor `int *v` de tamanho `n` com `realloc`?',
    explanation: 'Se o `realloc` falhar ele devolve NULL e o bloco antigo continua válido; guarde o retorno numa variável temporária.',
    options: [
      { text: '`int *t = realloc(v, 2*n*sizeof *v); if (t) v = t;`', correct: true },
      { text: '`v = realloc(v, 2*n*sizeof *v);`', feedback: 'Se o realloc falhar, perde o ponteiro antigo e vaza a memória.' },
      { text: '`free(v); v = realloc(v, 2*n*sizeof *v);`', feedback: 'Usa o ponteiro depois do free (uso após liberação).' },
      { text: '`realloc(v, 2*n*sizeof *v);` sem guardar o retorno', feedback: 'Acha que o realloc sempre aumenta no mesmo lugar; ele pode mover o bloco.' }
    ]
  },
  {
    activity: 'A1', correctAt: 2,
    statement: 'Quantas vezes o corpo de `for (i = 0; i < n; i++)` executa quando `n = 0`?',
    explanation: 'A condição `0 < 0` já é falsa no início, então o corpo não executa nenhuma vez.',
    options: [
      { text: 'Nenhuma', correct: true },
      { text: 'Uma', feedback: 'Acha que o `for` executa o corpo antes de testar a condição (isso é o `do while`).' },
      { text: 'Infinitas', feedback: 'Não percebe que a condição é testada antes da primeira volta.' },
      { text: 'n + 1', feedback: 'Off-by-one: confunde `i < n` com `i <= n`.' }
    ]
  },
  {
    activity: 'A2', correctAt: 3,
    statement: 'Na sua `strlen(s)`, qual condição de parada do laço está correta?',
    explanation: 'Strings em C terminam no caractere nulo `\'\\0\'`; o comprimento é o número de caracteres antes dele.',
    options: [
      { text: "`while (s[i] != '\\0') i++;`", correct: true },
      { text: '`while (s[i] != NULL) i++;`', feedback: 'Confunde o caractere nulo `\'\\0\'` com o ponteiro nulo `NULL`.' },
      { text: '`for (i = 0; i < sizeof(s); i++);`', feedback: 'Acha que `sizeof` de um ponteiro dá o tamanho da string.' },
      { text: "`while (s[i] != ' ') i++;`", feedback: 'Acha que a string termina no espaço em branco.' }
    ]
  },
  {
    activity: 'A3', correctAt: 4,
    statement: 'No insertion sort de `{5, 2, 4}`, como fica o vetor depois de inserir o segundo elemento (o 2)?',
    explanation: 'O 2 é comparado com a parte ordenada à esquerda (`{5}`) e entra antes dele: `{2, 5, 4}`.',
    options: [
      { text: '{2, 5, 4}', correct: true },
      { text: '{2, 4, 5}', feedback: 'Pula etapas: o 4 ainda não foi inserido nessa passada.' },
      { text: '{5, 2, 4}', feedback: 'Acha que a primeira passada só compara, sem mover nada.' },
      { text: '{4, 2, 5}', feedback: 'Confunde insertion sort com trocar o primeiro com o último.' }
    ]
  }
];

exports.seed = async function(knex) {
  for (const q of practice) {
    const activity = await knex('activity').where('title', 'like', `${q.activity} ·%`).first();
    if (!activity) throw new Error(`atividade "${q.activity}" não encontrada (rode o seed diagnostico_demo antes)`);
    const ref = `activity:${activity.id}`;
    if (await knex('question').where({ source_ref: ref, kind: 'practice' }).first()) continue;
    const [{ id }] = await knex('question').insert({
      skill_id: activity.skill_id, kind: 'practice', difficulty: activity.level_n,
      statement: q.statement, explanation: q.explanation, source_ref: ref
    }).returning('id');
    // A correta é a 1ª da lista; correctAt espalha a posição dela entre as questões.
    const n = q.options.length;
    await knex('question_option').insert(q.options.map((o, i) => ({
      question_id: id, text: o.text, is_correct: !!o.correct,
      position: (i + q.correctAt - 1) % n + 1, feedback: o.feedback || null
    })));
  }
};
