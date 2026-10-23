// Senha nunca em texto puro: user.hash só aceita argon2. Sem isso o security_db cai na
// comparação em texto puro (lib/auth/database.js) para qualquer hash que não comece com "$".
// Antes da trava, Ana e Bruno (demo) recebem o hash argon2id; qualquer outro hash em texto puro faz a migration falhar.
const DEMO_HASH = '$argon2id$v=19$m=65536,t=3,p=4$X92pu8rv4+dlifj79FB8Pw$fSUkXbXsac7dkO2XhgxKV4cmAySb9MDqMcs053e8VbI';

exports.up = async function(knex) {
  await knex('user').whereIn('username', ['ana', 'bruno']).whereNot('hash', 'like', '$argon2%').update({ hash: DEMO_HASH });
  await knex.raw(`alter table public."user" add constraint user_hash_argon2 check (hash like '$argon2%')`);
};

exports.down = function(knex) {
  return knex.raw(`alter table public."user" drop constraint if exists user_hash_argon2`);
};
