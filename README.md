# InstaFollow

InstaFollow e um site para descobrir quem tu segues no Instagram e nao te segue de volta. Abres o site, arrastas o `.zip` exportado pelo Instagram e recebes a lista no momento.

Site: [https://fialho14.github.io/InstaFollow/](https://fialho14.github.io/InstaFollow/)

Tudo corre no teu browser. Nao ha login, token, API, backend, extensoes nem envio dos teus ficheiros para servidores.

## Funcionalidades

- Aceita o `.zip` completo do export do Instagram.
- Aceita tambem JSON solto, desde que seleciones `following.json` e `followers_*.json` juntos.
- Compara `following.json` com `followers_*.json`.
- Remove automaticamente entradas apagadas como `__deleted__...`.
- Permite pesquisar usernames.
- Permite filtrar por pendentes, todos, retirados e indisponiveis.
- Permite ordenar por A-Z, mais recentes ou mais antigos.
- Guarda no browser apenas os estados que marcares como retirado ou indisponivel.
- Tambem funciona offline se abrires os ficheiros locais do projeto.

## Requisitos

- Um browser moderno, como Safari ou Chrome.
- Os teus dados do Instagram em formato JSON.

Nao precisas de correr Python para usar a app principal.

## Como obter os dados do Instagram

1. Abre o Instagram.
2. Vai a `Settings`.
3. Entra em `Accounts Centre`.
4. Entra em `Your information and permissions`.
5. Escolhe `Export your information`.
6. Escolhe `Create export`.
7. Seleciona a tua conta.
8. Seleciona `Export to device`.
9. No `Customise information` escolhe apenas `Followers and Following`.
10. No `Date range` escolhe  `All time`
11. Escolhe o formato `JSON`.
12. Faz download do ficheiro `.zip`.

O ZIP deve conter uma pasta parecida com:

```text
connections/followers_and_following/
```

Essa pasta costuma incluir:

```text
followers_1.json
following.json
following_hashtags.json
```

A app usa apenas `following.json` e `followers_*.json`.

## Como usar

Abre o site:

```text
https://fialho14.github.io/InstaFollow/
```

Depois arrasta o ficheiro `.zip` para o local indicado no site.

Tambem podes usar a versao local abrindo este ficheiro no Safari, Chrome ou outro browser:

```text
index.html
```

Depois carrega um destes formatos:

- O `.zip` completo exportado pelo Instagram.
- Ou os JSON soltos `following.json` e `followers_*.json`, selecionados ao mesmo tempo.

O resultado aparece na propria pagina. O dataset carregado fica so em memoria enquanto a pagina esta aberta.

## Estados guardados

Podes marcar perfis como:

- `Retirado`
- `Indisponivel`

Essas marcacoes ficam em `localStorage`, por username. A app nao guarda o export, a lista completa, nem os ficheiros JSON. Se limpares os dados do browser, as marcacoes podem desaparecer.

## ZIP offline

O suporte a ZIP usa uma dependencia local vendorizada:

```text
vendor/fflate.min.js
vendor/fflate.LICENSE.txt
```

Nao ha CDN externa. Mantem a pasta `vendor/` ao lado de `index.html`.

## Ferramenta Python opcional

O ficheiro `naoseguidores.py` continua disponivel para comparar no terminal. Por defeito, ele gera:

```text
nao_me_seguem_gerado.html
```

Exemplo:

```bash
python3 naoseguidores.py --path "/caminho/para/followers_and_following"
```

Este fluxo e auxiliar. A app principal e o site com upload local no browser.

## Privacidade

Os teus ficheiros do Instagram podem conter informacao pessoal. Nao envies para o GitHub pastas como:

```text
Instagram_data_*/
connections/
followers_and_following/
```

Tambem confirma antes de publicar ficheiros gerados pelo Python, porque podem conter usernames inline.

## Notas importantes

- A app nao deixa de seguir ninguem automaticamente.
- A app nao confirma online se um perfil existe.
- O Instagram pode mostrar paginas diferentes dependendo da tua sessao, privacidade, bloqueios ou contas desativadas.
- Se a lista parecer errada, faz um novo download dos dados do Instagram. O export pode estar desatualizado.
