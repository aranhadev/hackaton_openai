
exports.up = function(knex) {
  return knex.schema
    .withSchema('public')
    .renameTable('l', 'learning_path')
      .withSchema('public')
    .renameTable('learning_levels', 'learning_level')
  
};

exports.down = function(knex) {
  return knex.schema
    .withSchema('public')
    .renameTable('learning_level', 'learning_levels')
    .withSchema('public')
    .renameTable('learning_path', 'l')
};
