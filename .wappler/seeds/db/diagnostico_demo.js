// Seed da demo do diagnóstico (linguagem C).
// Requer a migration "trilha personalizada" (usa question_option.feedback).
// Cria: 5 questões diagnósticas (2 ponteiros, 2 memória, 1 algoritmos) com alternativas
// e feedback nas erradas; 9 atividades (3 habilidades x níveis 1-3); alunos Ana e Bruno.
// Idempotente: questões pela chave source_ref, atividades pelo title, alunos pelo username.
//
// Senha dos alunos: só o hash argon2id (DEMO_HASH) vai para o banco, nunca texto puro.
// A migration "user hash argon2" recusa qualquer hash que não seja argon2.
// Para gerar outro: node -e "require('argon2').hash('nova',{type:2}).then(console.log)" no container.
//
// Ordem das questões = question.id (P, P, M, M, A). Respostas da demo:
//   Ana   erra Q1 e Q2 (ponteiros)         -> P1 -> P2 -> P3 -> M3 -> A3
//   Bruno erra Q3 (memória) e Q5 (algoritmos) -> A1 -> A2 -> A3 -> M2 -> M3 -> P3

const DEMO_HASH = '$argon2id$v=19$m=65536,t=3,p=4$X92pu8rv4+dlifj79FB8Pw$fSUkXbXsac7dkO2XhgxKV4cmAySb9MDqMcs053e8VbI';

const questions = [
  {
    key: 'seed:diag:1', correctAt: 2, skill: 'ponteiros', difficulty: 1,
    statement: 'Dado `int x = 10; int *p = &x;`, o que `printf("%d", *p);` imprime?',
    explanation: '`p` guarda o endereço de `x`; `*p` lê o valor nesse endereço, que é 10.',
    options: [
      { text: '10', correct: true },
      { text: 'O endereço de memória de x', feedback: 'Confunde `*p` (valor apontado) com `p` (o endereço guardado).' },
      { text: '0', feedback: 'Acha que um ponteiro começa "zerado" mesmo depois de receber `&x`.' },
      { text: 'Erro de compilação', feedback: 'Acha que `*` só existe na declaração e não serve para desreferenciar.' }
    ]
  },
  {
    key: 'seed:diag:2', correctAt: 3, skill: 'ponteiros', difficulty: 2,
    statement: 'Dado `int v[3] = {1, 2, 3}; int *p = v; p++;`, quanto vale `*p`?',
    explanation: '`p++` avança um elemento inteiro (sizeof(int) bytes): `p` passa a apontar para `v[1]`, que vale 2.',
    options: [
      { text: '2', correct: true },
      { text: '1', feedback: 'Acha que `p++` não muda para onde o ponteiro aponta.' },
      { text: '2, mas só se int tiver 1 byte', feedback: 'Acha que aritmética de ponteiros soma bytes, não elementos.' },
      { text: '4', feedback: 'Confunde incrementar o ponteiro com incrementar o valor apontado (`(*p)++`).' }
    ]
  },
  {
    key: 'seed:diag:3', correctAt: 1, skill: 'memoria', difficulty: 1,
    statement: 'A função `int *f(void) { int x = 5; return &x; }` devolve um ponteiro. O que acontece ao usar esse ponteiro depois que `f` retorna?',
    explanation: '`x` vive na stack de `f`; quando `f` retorna, essa memória deixa de ser válida. Usar o ponteiro é comportamento indefinido.',
    options: [
      { text: 'Comportamento indefinido: x deixou de existir quando f retornou', correct: true },
      { text: 'Sempre lê 5', feedback: 'Não distingue o tempo de vida de variáveis locais (stack) de memória alocada (heap).' },
      { text: 'O compilador sempre impede esse código', feedback: 'Acha que aviso do compilador garante segurança; ele compila e o erro aparece em tempo de execução.' },
      { text: 'x só é liberado no fim do programa', feedback: 'Acha que variáveis locais vivem até o fim do programa, como globais.' }
    ]
  },
  {
    key: 'seed:diag:4', correctAt: 4, skill: 'memoria', difficulty: 2,
    statement: 'Depois de `char *s = malloc(10);` e de usar `s`, qual é a forma correta de liberar a memória e evitar uso após o free?',
    explanation: '`free` recebe o ponteiro devolvido por `malloc`; zerar `s` evita usar ou liberar de novo a mesma área.',
    options: [
      { text: '`free(s); s = NULL;`', correct: true },
      { text: '`free(*s);`', feedback: 'Confunde o ponteiro com o valor apontado na hora de liberar.' },
      { text: 'Não precisa: a memória é liberada quando a função termina', feedback: 'Confunde heap (malloc, liberação manual) com stack (liberação automática).' },
      { text: '`delete s;`', feedback: 'Mistura C com C++: em C a memória do malloc é liberada com free.' }
    ]
  },
  {
    key: 'seed:diag:5', correctAt: 2, skill: 'algoritmos', difficulty: 1,
    statement: 'Para somar um vetor `v` de `n` elementos: `for (i = 0; i <= n; i++) soma += v[i];`. Qual é o problema?',
    explanation: 'Os índices válidos vão de 0 a n-1. Com `i <= n` o laço lê `v[n]`, uma posição além do fim (off-by-one).',
    options: [
      { text: 'Lê v[n], uma posição além do fim do vetor', correct: true },
      { text: 'Nenhum, o laço está correto', feedback: 'Não reconhece o limite do vetor: em C os índices vão de 0 a n-1.' },
      { text: 'A soma fica sem o último elemento', feedback: 'Inverte o off-by-one: aqui o laço passa do fim, não para antes.' },
      { text: 'O i deveria começar em 1', feedback: 'Acha que vetores em C começam no índice 1.' }
    ]
  }
];

const activities = [
  { title: 'P1 · Endereço (&) e valor (*)', skill: 'ponteiros', level: 1,
    content: 'Declare `int x = 42; int *p = &x;` e imprima `x`, `&x`, `p` e `*p`. Depois altere `x` através de `*p`.',
    explanation: '`&` dá o endereço; `*` lê ou escreve no endereço guardado no ponteiro.' },
  { title: 'P2 · Aritmética de ponteiros e vetores', skill: 'ponteiros', level: 2,
    content: 'Percorra `int v[5]` usando só um ponteiro (`p++`) e imprima cada valor e cada endereço.',
    explanation: '`p + 1` avança `sizeof(*p)` bytes: um elemento, não um byte.' },
  { title: 'P3 · Ponteiro para ponteiro', skill: 'ponteiros', level: 3,
    content: 'Escreva `void troca(int **a, int **b)` que troca para onde dois ponteiros apontam.',
    explanation: 'Para alterar um ponteiro dentro de uma função, passe o endereço dele (`int **`).' },
  { title: 'M1 · Stack x heap: tempo de vida', skill: 'memoria', level: 1,
    content: 'Corrija `int *f(void) { int x = 5; return &x; }` para devolver memória válida.',
    explanation: 'Locais morrem ao sair da função; `malloc` vive até `free`.' },
  { title: 'M2 · malloc e free sem vazamento', skill: 'memoria', level: 2,
    content: 'Aloque um vetor de `n` ints com `malloc`, preencha, some e libere. Verifique com valgrind.',
    explanation: 'Todo `malloc` precisa de exatamente um `free`; teste sempre se o retorno é NULL.' },
  { title: 'M3 · realloc e uso após free', skill: 'memoria', level: 3,
    content: 'Implemente um vetor dinâmico que dobra de tamanho com `realloc`, sem perder o ponteiro original em caso de falha.',
    explanation: 'Guarde o retorno do `realloc` em uma variável temporária; nunca use um ponteiro já liberado.' },
  { title: 'A1 · Laços e limites de vetor', skill: 'algoritmos', level: 1,
    content: 'Escreva `int soma(int *v, int n)` e teste com n = 0, 1 e 5.',
    explanation: 'Índices válidos: 0 a n-1. Use `i < n`.' },
  { title: 'A2 · Busca linear em strings', skill: 'algoritmos', level: 2,
    content: 'Reimplemente `strlen` e `strchr` sem usar a biblioteca padrão.',
    explanation: 'Strings em C terminam em `\'\\0\'`; o laço para nele.' },
  { title: 'A3 · Ordenação por inserção', skill: 'algoritmos', level: 3,
    content: 'Ordene um vetor de ints com insertion sort e conte quantas trocas foram feitas.',
    explanation: 'Cada elemento é inserido na posição certa da parte já ordenada à esquerda.' }
];

const users = [
  { username: 'ana', name: 'Ana', persona: 'erra ponteiros' },
  { username: 'bruno', name: 'Bruno', persona: 'erra algoritmos e 1 de memória' }
];

exports.seed = async function(knex) {
  const skills = await knex('skill').select('id', 'code');
  const skillId = code => {
    const s = skills.find(s => s.code == code);
    if (!s) throw new Error(`skill "${code}" não encontrada`);
    return s.id;
  };

  for (const q of questions) {
    if (await knex('question').where('source_ref', q.key).first()) continue;
    const [{ id }] = await knex('question').insert({
      skill_id: skillId(q.skill), kind: 'diagnostic', difficulty: q.difficulty,
      statement: q.statement, explanation: q.explanation, source_ref: q.key
    }).returning('id');
    // A correta é a 1ª da lista; correctAt espalha a posição dela entre as questões.
    const n = q.options.length;
    await knex('question_option').insert(q.options.map((o, i) => ({
      question_id: id, text: o.text, is_correct: !!o.correct,
      position: (i + q.correctAt - 1) % n + 1, feedback: o.feedback || null
    })));
  }

  for (const a of activities) {
    if (await knex('activity').where('title', a.title).first()) continue;
    await knex('activity').insert({
      title: a.title, skill_id: skillId(a.skill), level_n: a.level,
      content: a.content, explanation: a.explanation
    });
  }

  for (const u of users) {
    const existing = await knex('user').where('username', u.username).first();
    if (existing) {
      if (!String(existing.hash || '').startsWith('$argon2')) {
        await knex('user').where('id', existing.id).update({ hash: DEMO_HASH });
      }
      continue;
    }
    await knex('user').insert({
      username: u.username, name: u.name, hash: DEMO_HASH,
      internal_data: { demo: true, persona: u.persona }
    });
  }
};
