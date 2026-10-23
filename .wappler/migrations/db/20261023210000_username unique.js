// Garante no banco o que a action auth/register checa (409): username único em user.
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('user', async function (table) {
      table.unique(['username']);
    })

};

exports.down = function(knex) {
  return knex.schema
    .withSchema('public')
    .table('user', async function (table) {
      table.dropUnique(['username']);
    })
};
