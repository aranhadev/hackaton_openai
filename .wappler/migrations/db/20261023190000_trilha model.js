// Modelo da trilha personalizada (C: ponteiros, algoritmos, gerenciamento de memória).
// Renomeia ativity -> activity, cria habilidades, banco de questões, trilhas, respostas
// do diagnóstico por tentativa, progresso e as views attempt_skill_score (histórico)
// e user_skill_score (score atual = última tentativa concluída).
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('ativity', async function (table) {
      table.dropForeign('main_learn_level', 'ativity_main_learn_level_foreign');
    })
    .withSchema('public')
    .renameTable('ativity', 'activity')
    .withSchema('public')
    .createTable('skill', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.string('code').notNullable().unique();
      table.string('title');
      table.text('description');
    })
    .withSchema('public')
    .table('activity', async function (table) {
      table.foreign('main_learn_level').references('id').inTable('public.learning_level').onUpdate('CASCADE').onDelete('SET NULL');
      table.integer('skill_id').unsigned();
      table.foreign('skill_id').references('id').inTable('public.skill').onUpdate('CASCADE').onDelete('RESTRICT');
      table.integer('level_n');
      table.string('kind').defaultTo('quiz');
      table.text('content');
      table.text('explanation');
      table.string('examshell_id');
    })
    .withSchema('public')
    .createTable('question', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.integer('skill_id').unsigned();
      table.foreign('skill_id').references('id').inTable('public.skill').onUpdate('CASCADE').onDelete('RESTRICT');
      table.string('kind').defaultTo('diagnostic');
      table.integer('difficulty').defaultTo(1);
      table.text('statement');
      table.text('explanation');
      table.string('source_ref');
      table.jsonb('internal_data');
    })
    .withSchema('public')
    .createTable('question_option', async function (table) {
      table.increments('id');
      table.integer('question_id').unsigned();
      table.foreign('question_id').references('id').inTable('public.question').onUpdate('CASCADE').onDelete('CASCADE');
      table.text('text');
      table.boolean('is_correct').defaultTo(false);
      table.integer('position');
    })
    .withSchema('public')
    .table('learning_path', async function (table) {
      table.integer('skill_id').unsigned();
      table.foreign('skill_id').references('id').inTable('public.skill').onUpdate('CASCADE').onDelete('RESTRICT');
      table.text('description');
    })
    .withSchema('public')
    .createTable('learning_path_step', async function (table) {
      table.increments('id');
      table.integer('learning_path_id').unsigned();
      table.foreign('learning_path_id').references('id').inTable('public.learning_path').onUpdate('CASCADE').onDelete('CASCADE');
      table.integer('activity_id').unsigned();
      table.foreign('activity_id').references('id').inTable('public.activity').onUpdate('CASCADE').onDelete('RESTRICT');
      table.integer('position');
      table.unique(['learning_path_id', 'position']);
    })
    // Cada vez que o aluno faz o diagnóstico vira uma tentativa (histórico completo).
    .withSchema('public')
    .createTable('diagnostic_attempt', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.integer('user_id').unsigned();
      table.foreign('user_id').references('id').inTable('public.user').onUpdate('CASCADE').onDelete('CASCADE');
      table.string('status').defaultTo('in_progress');
      table.timestamp('finished_at');
    })
    .withSchema('public')
    .createTable('diagnostic_answer', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.integer('attempt_id').unsigned();
      table.foreign('attempt_id').references('id').inTable('public.diagnostic_attempt').onUpdate('CASCADE').onDelete('CASCADE');
      table.integer('user_id').unsigned();
      table.foreign('user_id').references('id').inTable('public.user').onUpdate('CASCADE').onDelete('CASCADE');
      table.integer('question_id').unsigned();
      table.foreign('question_id').references('id').inTable('public.question').onUpdate('CASCADE').onDelete('RESTRICT');
      table.integer('option_id').unsigned();
      table.foreign('option_id').references('id').inTable('public.question_option').onUpdate('CASCADE').onDelete('SET NULL');
      table.boolean('is_correct');
      table.unique(['attempt_id', 'question_id']);
    })
    .withSchema('public')
    .createTable('user_path', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.integer('user_id').unsigned();
      table.foreign('user_id').references('id').inTable('public.user').onUpdate('CASCADE').onDelete('CASCADE');
      table.integer('learning_path_id').unsigned();
      table.foreign('learning_path_id').references('id').inTable('public.learning_path').onUpdate('CASCADE').onDelete('RESTRICT');
      table.integer('attempt_id').unsigned();
      table.foreign('attempt_id').references('id').inTable('public.diagnostic_attempt').onUpdate('CASCADE').onDelete('SET NULL');
      table.jsonb('reason');
      table.boolean('is_active').defaultTo(true);
    })
    .withSchema('public')
    .createTable('activity_progress', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.integer('user_id').unsigned();
      table.foreign('user_id').references('id').inTable('public.user').onUpdate('CASCADE').onDelete('CASCADE');
      table.integer('activity_id').unsigned();
      table.foreign('activity_id').references('id').inTable('public.activity').onUpdate('CASCADE').onDelete('CASCADE');
      table.string('status').defaultTo('pending');
      table.integer('attempts').defaultTo(0);
      table.timestamp('completed_at');
      table.string('source').defaultTo('web');
      table.unique(['user_id', 'activity_id']);
    })
    // Habilidades fixas do desafio: a view e as trilhas dependem delas.
    .raw(`
      insert into public.skill (code, title, description) values
        ('ponteiros', 'Ponteiros', 'Endereços, desreferência, aritmética de ponteiros e ponteiros para ponteiros.'),
        ('algoritmos', 'Algoritmos', 'Laços, condições, manipulação de strings e arrays, busca e ordenação.'),
        ('memoria', 'Gerenciamento de memória', 'Stack x heap, malloc/free, vazamentos e acesso inválido.')
    `)
    // Score por tentativa x habilidade (histórico: compara antes/depois).
    .raw(`
      create view public.attempt_skill_score as
      select
        a.id as attempt_id,
        a.user_id,
        a.finished_at,
        s.id as skill_id,
        s.code as skill_code,
        count(da.id)::int as answered,
        count(da.id) filter (where da.is_correct)::int as correct,
        case when count(da.id) = 0 then null
             else round(count(da.id) filter (where da.is_correct)::numeric / count(da.id), 2)
        end as score
      from public.diagnostic_attempt a
      cross join public.skill s
      left join public.question q on q.skill_id = s.id and q.kind = 'diagnostic'
      left join public.diagnostic_answer da on da.question_id = q.id and da.attempt_id = a.id
      group by a.id, a.user_id, a.finished_at, s.id, s.code
    `)
    // Score atual do aluno: só a última tentativa concluída (usado para escolher a trilha).
    .raw(`
      create view public.user_skill_score as
      select ass.user_id, ass.attempt_id, ass.skill_id, ass.skill_code, ass.answered, ass.correct, ass.score
      from public.attempt_skill_score ass
      where ass.attempt_id = (
        select a2.id from public.diagnostic_attempt a2
        where a2.user_id = ass.user_id and a2.status = 'finished'
        order by a2.finished_at desc, a2.id desc
        limit 1
      )
    `)
};

exports.down = function(knex) {
  return knex.schema
    .raw('drop view if exists public.user_skill_score')
    .raw('drop view if exists public.attempt_skill_score')
    .withSchema('public')
    .dropTable('activity_progress')
    .withSchema('public')
    .dropTable('user_path')
    .withSchema('public')
    .dropTable('diagnostic_answer')
    .withSchema('public')
    .dropTable('diagnostic_attempt')
    .withSchema('public')
    .dropTable('learning_path_step')
    .withSchema('public')
    .table('learning_path', async function (table) {
      table.dropForeign('skill_id');
      table.dropColumn('skill_id');
      table.dropColumn('description');
    })
    .withSchema('public')
    .dropTable('question_option')
    .withSchema('public')
    .dropTable('question')
    .withSchema('public')
    .table('activity', async function (table) {
      table.dropForeign('skill_id');
      table.dropForeign('main_learn_level');
      table.dropColumn('skill_id');
      table.dropColumn('level_n');
      table.dropColumn('kind');
      table.dropColumn('content');
      table.dropColumn('explanation');
      table.dropColumn('examshell_id');
    })
    .withSchema('public')
    .dropTable('skill')
    .withSchema('public')
    .renameTable('activity', 'ativity')
    .withSchema('public')
    .table('ativity', async function (table) {
      table.foreign('main_learn_level', 'ativity_main_learn_level_foreign').references('id').inTable('public.learning_level').onUpdate('CASCADE').onDelete('CASCADE');
    })
};
