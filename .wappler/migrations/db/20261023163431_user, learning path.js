
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .createTable('user', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.string('name');
    })
    .withSchema('public')
    .createTable('l', async function (table) {
      table.increments('id');
      table.timestamp('creation_dt').defaultTo(knex.fn.now());
      table.string('title');
    })

};

exports.down = function(knex) {
  return knex.schema
    .withSchema('public')
    .dropTable('l')
    .withSchema('public')
    .dropTable('user')
};
