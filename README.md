# CubeDvij Modpack

![Aggregate Modpacks](../../actions/workflows/aggregate-modpacks.yml/badge.svg)

Репозиторій збірок модів CubeDvij. Кожна гілка містить окрему збірку у форматі Modrinth.

## 📦 Збірки

Актуальний список збірок автоматично генерується у [`modpacks.json`](../../releases/download/meta/modpacks.json).

Завантажити `.mrpack` файли можна у [Releases](../../releases/tag/meta) або на [сторінці збірок](../../deployments/github-pages).

## 🔧 Як це працює

При пуші в будь-яку гілку (окрім `main`) автоматично:
1. Парситься `modrinth.index.json` з усіх гілок
2. Збирається `modpacks.json` з метаданими
3. Будуються `.mrpack` файли для кожної збірки
4. Все завантажується у GitHub Release `meta`
5. Генерується HTML-сторінка зі списком збірок на GitHub Pages
