# Readers

{{ read_json('people.json') }}

{{ read_yaml('people.yaml') }}

{{ read_csv('people.csv', sep=';', usecols=['Name']) }}

{{ read_tsv('unread.tsv') }}
