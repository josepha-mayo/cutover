// Deterministic starter for the bounded two-column SQLite contract. Every
// generated contract and plan still goes through the server's SQL validator.
const identifier = /^[A-Za-z_][A-Za-z0-9_]{0,62}$/;

export function buildScenario(input) {
  const project = String(input.project || '').trim();
  const table = String(input.table || '').trim();
  const oldColumn = String(input.oldColumn || '').trim();
  const newColumn = String(input.newColumn || '').trim();
  const values = [String(input.firstValue ?? ''), String(input.secondValue ?? '')];
  const incomingValue = String(input.incomingValue ?? '');
  if (!project || project.length > 100) throw Error('Give this scenario a name of at most 100 characters.');
  for (const [label, name] of [['Table', table], ['Old column', oldColumn], ['New column', newColumn]]) {
    if (!identifier.test(name)) throw Error(`${label} must be a simple SQL identifier of at most 63 characters.`);
  }
  if (oldColumn.toLowerCase() === newColumn.toLowerCase()) throw Error('Old and new column names must differ.');
  if (oldColumn.toLowerCase() === 'id' || newColumn.toLowerCase() === 'id')
    throw Error('The id column is reserved for record identity.');
  if (values.some(value => !value || value.length > 1000))
    throw Error('Enter two nonempty sample values of at most 1000 characters.');
  if (!incomingValue || incomingValue.length > 1000)
    throw Error('Enter the exact incoming write to protect (at most 1000 characters).');
  const payloads = [incomingValue];
  for (const sample of ["O'Connell", '0', '東京-棚', 'next release']) {
    if (payloads.length === 4) break;
    if (!payloads.includes(sample)) payloads.push(sample);
  }
  const q = name => `"${name}"`;
  const t = q(table), old = q(oldColumn), next = q(newColumn);
  const read = `SELECT id, ${next} AS value FROM ${t} ORDER BY id`;
  const write = `UPDATE ${t} SET ${next} = :value WHERE id = :id`;
  const insert = `INSERT INTO ${t} (id, ${old}, ${next}) VALUES (:id, :value, :value)`;
  const contract = {
    project,
    summary: `Rehearse ${oldColumn} → ${newColumn} while old ${table} workers still read and write.`,
    old_column: oldColumn, new_column: newColumn, table,
    schema: `CREATE TABLE ${t} (id INTEGER PRIMARY KEY, ${old} TEXT NOT NULL);`,
    seed_sql: `INSERT INTO ${t} (id, ${old}) VALUES (?, ?)`,
    seed: [[1, values[0]], [2, values[1]]],
    old: {
      read: `SELECT id, ${old} AS value FROM ${t} ORDER BY id`,
      write: `UPDATE ${t} SET ${old} = :value WHERE id = :id`,
      insert: `INSERT INTO ${t} (id, ${old}) VALUES (:id, :value)`
    },
    payloads
  };
  const unsafe = {
    name: 'One-time backfill without a compatibility bridge',
    migration: `ALTER TABLE ${t} ADD COLUMN ${next} TEXT;\nUPDATE ${t} SET ${next} = ${old};`,
    read, write, insert
  };
  const safe = {
    name: 'Generated compatibility bridge · verify before use',
    migration: `ALTER TABLE ${t} ADD COLUMN ${next} TEXT;\n`+
      `CREATE TRIGGER cutover_old_update AFTER UPDATE OF ${old} ON ${t}\n`+
      `WHEN NEW.${old} IS NOT NEW.${next}\nBEGIN\n`+
      `  UPDATE ${t} SET ${next} = NEW.${old} WHERE id = NEW.id;\nEND;\n`+
      `CREATE TRIGGER cutover_new_update AFTER UPDATE OF ${next} ON ${t}\n`+
      `WHEN NEW.${next} IS NOT NEW.${old}\nBEGIN\n`+
      `  UPDATE ${t} SET ${old} = NEW.${next} WHERE id = NEW.id;\nEND;\n`+
      `CREATE TRIGGER cutover_old_insert AFTER INSERT ON ${t}\n`+
      `WHEN NEW.${next} IS NULL\nBEGIN\n`+
      `  UPDATE ${t} SET ${next} = NEW.${old} WHERE id = NEW.id;\nEND;\n`+
      `UPDATE ${t} SET ${next} = ${old};`,
    read, write, insert
  };
  return {contract, unsafe, safe};
}
