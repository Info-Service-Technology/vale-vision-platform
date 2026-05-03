# Runbook Git Branching Vision

## Objetivo

Manter a versao atual estavel em producao enquanto a nova interface `MDBootstrap v2` evolui em paralelo sem risco de PR acidental.

## Branches

- `feature/mauroslucios`
  - trilha da versao atual
  - base do que pode seguir para producao
- `feature/mdbootstrap-v2`
  - laboratorio da nova interface
  - pode receber `push`, mas nao deve gerar PR
- `release/mdbootstrap-v2`
  - branch de integracao da v2
  - nasce apenas quando a v2 estiver madura
  - unica branch da v2 que pode abrir PR para `main`

## Fluxo Da Versao Atual

Quando for trabalhar na versao atual:

```bash
git checkout feature/mauroslucios
git pull origin feature/mauroslucios
```

Depois das mudancas:

```bash
git add .
git commit -m "Sua mensagem"
git push origin feature/mauroslucios
```

Quando estiver pronto para producao:

- abrir PR de `feature/mauroslucios` para `main`

## Fluxo Da V2

Quando for trabalhar na nova interface:

```bash
git checkout feature/mdbootstrap-v2
git pull origin feature/mdbootstrap-v2
```

Depois das mudancas:

```bash
git add .
git commit -m "Sua mensagem"
git push origin feature/mdbootstrap-v2
```

Regras:

- a branch pode subir para o GitHub
- nao abrir PR dessa branch

## Promocao Da V2

Quando a v2 estiver madura:

```bash
git checkout feature/mdbootstrap-v2
git pull origin feature/mdbootstrap-v2
git checkout -b release/mdbootstrap-v2
git push -u origin release/mdbootstrap-v2
```

Depois:

- revisar
- testar
- corrigir
- abrir PR de `release/mdbootstrap-v2` para `main`

## Alternancia Rapida

Para voltar para a versao atual:

```bash
git checkout feature/mauroslucios
```

Para voltar para a v2:

```bash
git checkout feature/mdbootstrap-v2
```

## Regra De Ouro

- `feature/mauroslucios` = producao atual
- `feature/mdbootstrap-v2` = laboratorio
- `release/mdbootstrap-v2` = unica branch da v2 autorizada a virar PR

