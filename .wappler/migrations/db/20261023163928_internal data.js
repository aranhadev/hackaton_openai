
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('ativity', async function (table) {
      table.jsonb('internal_data');
      table.integer('main_learn_level').unsigned();
      table.foreign('main_learn_level').references('id').inTable('public.learning_level').onUpdate('CASCADE').onDelete('CASCADE');
    })
    .withSchema('public')
    .table('learning_level', async function (table) {
      table.jsonb('internal_data');
    })
    .withSchema('public')
    .table('learning_path', async function (table) {
      table.jsonb('internal_data');
    })
    .withSchema('public')
    .table('user', async function (table) {
      table.jsonb('internal_data');
    })

};

exports.down = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('user', async function (table) {
      table.dropColumn('internal_data');
    })
    .withSchema('public')
    .table('learning_path', async function (table) {
      table.dropColumn('internal_data');
    })
    .withSchema('public')
    .table('learning_level', async function (table) {
      table.dropColumn('internal_data');
    })
    .withSchema('public')
    .table('ativity', async function (table) {
      table.dropColumn('internal_data');
      table.dropForeign('main_learn_level');
      table.dropColumn('main_learn_level');
    })
};
