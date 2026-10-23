
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .createTable('ativity', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.string('title');
    })
    .withSchema('public')
    .createTable('learning_levels', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.string('title');
      table.integer('level_n');
    })
    .withSchema('public')
    .table('user', async function (table) {
      table.string('hash');
    })

};

exports.down = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('user', async function (table) {
      table.dropColumn('hash');
    })
    .withSchema('public')
    .dropTable('learning_levels')
    .withSchema('public')
    .dropTable('ativity')
};
