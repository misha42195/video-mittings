# Как запустить проект

Все команды ниже выполняются из корня репозитория (`video-meetings`), если явно не указано иное.

## 1. Поднять базу данных

```bash
docker compose up -d
```

Проверить, что контейнер здоровый:

```bash
docker compose ps
```

## 2. Установить зависимости

```bash
npm install                          # корень + apps/web (npm workspaces)
cd apps/api && uv sync && cd ../..   # venv для apps/api (uv)
```

## 3. Настроить переменные окружения для API

Один раз, при первом запуске:

```bash
cp apps/api/.env.example apps/api/.env
```

Значения по умолчанию уже указывают на локальный postgres из `docker-compose.yml` — менять не обязательно (кроме `JWT_SECRET_KEY` при выкладке в прод).

## 4. Запустить серверы разработки

Из корня:

```bash
npm run dev          # web (:3000) + api (:8000) одновременно
```

Или по отдельности:

```bash
npm run dev:web        # только web — http://localhost:3000
npm run dev:api        # только api — http://localhost:8000 (docs: /docs)
```

Команда `npm run dev` держит процесс в консоли — для дальнейших проверок открывать новый терминал.

## 5. Проверить работоспособность

### Автотесты

Из корня (нужен запущенный postgres, шаг 1):

```bash
npm run test          # алиас для test:api — apps/web тестов пока нет
```

Точечно из `apps/api`:

```bash
cd apps/api && uv run pytest
```

### Вручную через Swagger UI

Открыть в браузере: http://localhost:8000/docs — там есть формы для `/auth/register` и `/auth/login` с кнопкой "Try it out".

### Вручную через curl

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"supersecret123"}'

curl -X POST http://localhost:8000/auth/login \
  -d 'username=test@example.com&password=supersecret123'
```

Оба auth-эндпоинта должны вернуть `{"access_token": "...", "token_type": "bearer"}`.

### Web

Открыть http://localhost:3000 — сейчас там стандартная заглушка create-next-app, фронтенд с auth пока не подключён.

## 6. Линт, форматирование, типы (не про запуск, но полезно перед коммитом)

```bash
npm run lint
npm run format
npm run typecheck
```

У каждой из этих команд, а также у `build` и `test`, есть варианты `:web` / `:api` для запуска только на одном приложении (например `npm run lint:api`).

## Где что лежит (для IDE)

- Python-пакет `api` находится в `apps/api/src/api/` — в PyCharm нужно пометить `apps/api/src` как **Sources Root**, чтобы резолвились импорты вида `from api.database import Base`.
- Python-интерпретатор проекта: `apps/api/.venv/bin/python3`.
- Frontend (`apps/web`) резолвит пути через свой `tsconfig.json` (`@/*` → `apps/web/src/*`), отдельно ничего маркировать не нужно.
