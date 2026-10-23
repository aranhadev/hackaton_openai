
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('user', async function (table) {
      table.string('username');
    })

};

exports.down = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('user', async function (table) {
      table.dropColumn('username');
    })
};
