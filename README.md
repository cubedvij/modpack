# CubeDvij Modpack

![Aggregate Modpacks](../../actions/workflows/aggregate-modpacks.yml/badge.svg)

Репозиторий сборок модов CubeDvij. Каждая ветка содержит отдельную сборку в формате Modrinth.

## 📦 Сборки

Актуальный список сборок автоматически генерируется в [`modpacks.json`](../../releases/download/meta/modpacks.json).

Скачать `.mrpack` файлы можно в [Releases](../../releases/tag/meta) или на [странице сборок](../../deployments/github-pages).

## 🔧 Как это работает

При пуше в любую ветку (кроме `main`) автоматически:
1. Парсится `modrinth.index.json` из всех веток
2. Собирается `modpacks.json` с метаданными
3. Строятся `.mrpack` файлы для каждой сборки
4. Всё загружается в GitHub Release `meta`
5. Генерируется HTML-страница со списком сборок на GitHub Pages
