// Trilha montada por aluno: cada tentativa do diagnóstico gera uma sequência própria
// de atividades (view attempt_path_plan), gravada em user_path_step no finish.
// Regra: score < 0.5 -> começa no nível 1; < 1 -> nível 2; 1 -> nível 3.
// Ordem: habilidade mais fraca primeiro; empate por skill.sort_order
// (ponteiros -> memória -> algoritmos). Também cria question_option.feedback.
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('skill', async function (table) {
      table.integer('sort_order');
    })
    .raw(`
      update public.skill set sort_order = case code
        when 'ponteiros' then 1
        when 'memoria' then 2
        when 'algoritmos' then 3
      end
    `)
    .withSchema('public')
    .table('question_option', async function (table) {
      table.text('feedback');
    })
    .withSchema('public')
    .createTable('user_path_step', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.integer('user_path_id').unsigned();
      table.foreign('user_path_id').references('id').inTable('public.user_path').onUpdate('CASCADE').onDelete('CASCADE');
      table.integer('activity_id').unsigned();
      table.foreign('activity_id').references('id').inTable('public.activity').onUpdate('CASCADE').onDelete('RESTRICT');
      table.integer('skill_id').unsigned();
      table.foreign('skill_id').references('id').inTable('public.skill').onUpdate('CASCADE').onDelete('RESTRICT');
      table.integer('position');
      table.text('reason');
      table.unique(['user_path_id', 'position']);
    })
    // Plano de trilha por tentativa (aparece no DB Manager; o finish copia para user_path_step).
    .raw(`
      create view public.attempt_path_plan as
      with sc as (
        select
          ass.attempt_id,
          ass.user_id,
          ass.skill_id,
          ass.skill_code,
          ass.score,
          case
            when ass.score is null or ass.score < 0.5 then 1
            when ass.score < 1 then 2
            else 3
          end as start_level,
          row_number() over (
            partition by ass.attempt_id
            order by ass.score asc nulls first, s.sort_order asc, s.id asc
          ) as skill_rank
        from public.attempt_skill_score ass
        join public.skill s on s.id = ass.skill_id
      )
      select
        sc.attempt_id,
        sc.user_id,
        row_number() over (
          partition by sc.attempt_id
          order by sc.skill_rank, a.level_n, a.id
        )::int as position,
        a.id as activity_id,
        a.title as activity_title,
        a.level_n,
        sc.skill_id,
        sc.skill_code,
        sc.skill_rank::int as skill_rank,
        sc.score,
        sc.start_level,
        sc.skill_code || ': score ' || coalesce(sc.score::text, 'sem resposta')
          || ' -> começa no nível ' || sc.start_level as reason
      from sc
      join public.activity a on a.skill_id = sc.skill_id and a.level_n >= sc.start_level
    `)
};

exports.down = function(knex) {
  return knex.schema
    .raw('drop view if exists public.attempt_path_plan')
    .withSchema('public')
    .dropTable('user_path_step')
    .withSchema('public')
    .table('question_option', async function (table) {
      table.dropColumn('feedback');
    })
    .withSchema('public')
    .table('skill', async function (table) {
      table.dropColumn('sort_order');
    })
};
