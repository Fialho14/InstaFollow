# InstaFollow

InstaFollow e uma ferramenta local para descobrir quem tu segues no Instagram e nao te segue de volta. O script le os ficheiros JSON exportados pelo Instagram e gera uma pagina HTML bonita, pesquisavel e facil de usar no browser.

Tudo corre no teu computador. Nao precisas de login, token, API nem extensoes.

## Funcionalidades

- Compara `following.json` com `followers_*.json`.
- Remove automaticamente entradas apagadas que aparecem como `__deleted__...`.
- Gera `nao_me_seguem.html` com uma interface estilo Apple.
- Permite pesquisar usernames.
- Permite filtrar por:
  - pendentes
  - todos
  - retirados
  - indisponiveis
- Permite ordenar por A-Z, mais recentes ou mais antigos.
- Guarda no Safari/Chrome os perfis que ja marcaste como retirados ou indisponiveis.
- Funciona offline depois de gerada a pagina.

## Requisitos

- Python 3.10 ou mais recente.
- Os teus dados do Instagram em formato JSON.

Nao ha dependencias externas. O script usa apenas bibliotecas standard do Python.

## Como obter os dados do Instagram

1. Abre o Instagram.
2. Vai a `Settings`.
3. Entra em `Your information and permissions`.
4. Escolhe `Download your information`.
5. Seleciona apenas `Followers and Following`.
6. Escolhe o formato `JSON`.
7. Faz download do ficheiro `.zip`.
8. Extrai o `.zip`.
9. Procura a pasta:

```text
connections/followers_and_following/
```

Essa pasta deve conter ficheiros como:

```text
followers_1.json
following.json
following_hashtags.json
```

O script usa apenas `following.json` e `followers_*.json`.

## Como usar

Dentro da pasta do projeto, corre:

```bash
python3 naoseguidores.py --path "/caminho/para/followers_and_following"
```

Exemplo:

```bash
python3 naoseguidores.py --path "/Users/teu_nome/Downloads/instagram_data/connections/followers_and_following"
```

No fim, o script cria ou atualiza este ficheiro:

```text
nao_me_seguem.html
```

Abre esse ficheiro no Safari, Chrome ou outro browser.

No macOS tambem podes abrir pelo terminal:

```bash
open nao_me_seguem.html
```

## Como usar a pagina

- Usa a pesquisa para encontrar um username.
- Clica em `Abrir` para abrir o perfil no Instagram.
- Marca a checkbox quando ja deixaste de seguir essa conta.
- Clica em `Erro` quando o perfil abrir numa pagina de erro ou estiver indisponivel.
- Usa os filtros para veres so o que ainda falta.

As marcacoes ficam guardadas no browser atraves de `localStorage`. Se limpares os dados do browser, essas marcacoes podem desaparecer.

## Privacidade

Os teus ficheiros do Instagram podem conter informacao pessoal. Nao envies para o GitHub pastas como:

```text
Instagram_data_*/
connections/
followers_and_following/
```

O ficheiro `nao_me_seguem.html` tambem contem a lista de usernames gerada. Se o repositorio for publico, confirma antes de o publicar.

## Notas importantes

- O script nao deixa de seguir ninguem automaticamente.
- O script nao consegue garantir online se um perfil existe, porque o Instagram pode mostrar paginas diferentes dependendo da tua sessao, privacidade, bloqueios ou contas desativadas.
- Perfis claramente apagados no export do Instagram, como `__deleted__...`, sao removidos automaticamente.

## Problemas comuns

### `following.json` nao encontrado

Confirma que passaste o caminho correto para a pasta `followers_and_following`, nao para a pasta principal do download.

### A lista parece errada

Faz um novo download dos dados do Instagram. O export pode estar desatualizado se seguiste ou deixaste de seguir pessoas depois de o criares.

### As marcacoes desapareceram

As marcacoes ficam guardadas no browser. Podem desaparecer se limpares historico/dados do site ou se abrires a pagina noutro browser.
