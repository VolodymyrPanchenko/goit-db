## Налаштування оточення та запуск проєкту

### 1. Клонування / відкриття проєкту

Спочатку потрібно відкрити папку проєкту у VS Code або перейти в неї через термінал:

```bash
cd musicmongotask
```

### 2. Створення віртуального оточення

```bash
python -m venv .venv
```

Активація на Windows:

```bash
.venv\Scripts\activate
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

Файл `requirements.txt` містить необхідні Python-залежності, зокрема `pymongo`, `pandas`, `python-dotenv`, `tqdm`.

### 4. Налаштування `.env`

У корені проєкту потрібно створити файл `.env` і додати MongoDB Atlas connection string:

```
MONGO_URI=mongodb+srv://USERNAME:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
```

Значення `USERNAME`, `PASSWORD` та адресу кластера потрібно замінити на власні дані з MongoDB Atlas.

### 5. Завантаження сирих даних

Файл `dataset.csv` має бути розміщений у корені проєкту.

Після цього потрібно запустити скрипт завантаження даних:

```bash
python scripts/load_data.py
```

Скрипт створює базу `spotify` і завантажує сирі дані в колекцію `tracks_raw`.

### 6. Трансформація даних

Після завантаження сирих даних потрібно виконати трансформацію:

```bash
mongosh "ВАШ_MONGO_URI" --file scripts/02_transform.js
```

Цей скрипт створює колекцію `tracks` на основі `tracks_raw`, формує масив `artists`, вкладений об'єкт `audio_features`, поле `duration_sec` та `popularity_tier`.

### 7. Запуск запитів

Для виконання запитів до трансформованої колекції:

```bash
mongosh "ВАШ_MONGO_URI" --file queries/part2_queries.js
mongosh "ВАШ_MONGO_URI" --file queries/part3_aggregations.js
```

### 8. Аналіз індексів

Для виконання завдань з індексації:

```bash
mongosh "ВАШ_MONGO_URI" --file queries/part4_indexes.js
```

Скрипт виконує `explain()` до створення індексів, створює compound indexes і повторно виконує `explain()` для порівняння планів виконання.

## Схема даних

Після трансформації дані зберігаються в колекції `tracks` бази `spotify`. Кожен документ описує один музичний трек.

Підсумкова структура документа:

- `track_id` — ідентифікатор треку
- `track_name` — назва треку
- `album_name` — назва альбому
- `artists` — масив виконавців
- `explicit` — ознака explicit-контенту
- `popularity` — популярність треку
- `duration_ms` — тривалість у мілісекундах
- `duration_sec` — тривалість у секундах
- `track_genre` — жанр треку
- `popularity_tier` — категорія популярності: `high`, `medium`, `low`
- `audio_features` — вкладений об'єкт з аудіо-характеристиками треку

Приклад документа:

```json
{
  "_id": "ObjectId('6a3d08389bbdcc89d1640d5b')",
  "track_id": "6Vc5wAMmXdKIAM7WUoEb7N",
  "track_name": "Say Something",
  "album_name": "Is There Anybody Out There?",
  "artists": [
    "A Great Big World",
    "Christina Aguilera"
  ],
  "explicit": false,
  "popularity": 74,
  "duration_ms": 229400,
  "duration_sec": 229.4,
  "track_genre": "acoustic",
  "popularity_tier": "high",
  "audio_features": {
    "danceability": 0.407,
    "energy": 0.147,
    "loudness": -8.822,
    "speechiness": 0.0355,
    "acousticness": 0.857,
    "instrumentalness": 0.00000289,
    "liveness": 0.0913,
    "valence": 0.0765,
    "tempo": 141.284,
    "key": 2,
    "mode": 1,
    "time_signature": 3
  }
}
```

У фінальній схемі артисти зберігаються як масив, а аудіо-характеристики згруповані у вкладений об'єкт `audio_features`. Це робить документ більш структурованим і зручним для запитів.

## Теоретичні питання

### Частина 1 — Завантаження даних та проєктування схеми

**1) Чому аудіо-характеристики винесені в окремий об'єкт?**

Аудіо-характеристики винесені в окремий об'єкт `audio_features`, тому що вони логічно належать до однієї групи властивостей треку. Це робить структуру документа більш структурованою: загальна інформація про трек зберігається окремо від його технічних аудіо-параметрів.

Таке вкладення вигідне, коли група полів часто використовується разом і завжди належить одному документу.

Проблеми можуть виникати, якщо вкладена структура стає занадто складною або якщо по багатьох вкладених полях потрібно часто будувати складні індекси. Але для цієї задачі вкладення `audio_features` виглядає виправданим.

**2) Чому виконавці зберігаються як масив?**

Виконавці зберігаються як масив, тому що один трек може мати кількох артистів. Це дозволяє легко шукати треки конкретного виконавця.

Також масив спрощує запити з `$all`, `$in` та агрегації через `$unwind`, наприклад для підрахунку статистики по кожному артисту.

Якби виконавці зберігались одним рядком, такі запити були б більш громіздкими і вимагали б додаткового розбору рядка.

**3) Що таке `$out` і чим він відрізняється від `$merge`?**

`$out` записує результат aggregation pipeline у нову колекцію або повністю замінює існуючу колекцію результатом запиту. Його зручно використовувати, коли потрібно заново створити колекцію з трансформованими даними.

`$merge` також записує результат aggregation в колекцію, але працює гнучкіше: він може оновлювати існуючі документи, додавати нові або замінювати документи за заданим правилом.

- `$out` краще використовувати, коли потрібно повністю перегенерувати колекцію.
- `$merge` краще використовувати, коли потрібно оновити або доповнити вже існуючу колекцію без повного перезапису.

### Частина 2 — Запити до даних

**1) Для чого використовується `$unwind`?**

`$unwind` використовується для розгортання масиву в окремі документи. Якщо в документі поле `artists` містить кілька виконавців, то `$unwind` створює окремий запис для кожного артиста. Це зручно для групування і підрахунку статистики по кожному виконавцю окремо.

**2) Чим `$stdDevPop` відрізняється від `$stdDevSamp`?**

`$stdDevPop` рахує стандартне відхилення для всієї генеральної сукупності, тобто коли ми вважаємо, що маємо всі потрібні дані.

`$stdDevSamp` рахує стандартне відхилення для вибірки, тобто коли дані є лише частиною більшої сукупності.

### Завдання 3. Найбільш «танцювальний» жанр

**1) У запиті 1 ми фільтруємо виконавців, у яких менше 5 треків. Як зміниться результат, якщо знизити поріг до 1? А що станеться, якщо вибирати виконавців із більш ніж 50 треками?**

Якщо знизити поріг до 1 треку, у результат можуть потрапити виконавці з одним дуже популярним треком. Їхня середня популярність може бути високою, але такий результат менш надійний статистично, бо базується лише на одному або кількох треках.

Якщо вибирати тільки виконавців із більш ніж 50 треками, результат стане більш стабільним, бо середня популярність буде рахуватися на великій кількості треків. Але багато виконавців буде відфільтровано, тому в результаті залишаться переважно артисти з великою дискографією. Вони можуть мати нижчу середню популярність, бо серед багатьох треків зазвичай є як популярні, так і менш популярні.

**2) У запиті 3 ми фільтруємо жанри з менше ніж 100 треками. Чи зміниться результат, якщо знизити поріг до 50?**

Так, результат може змінитися. Якщо знизити поріг до 50 треків, у вибірку потрапить більше жанрів. Серед них можуть бути жанри з високими середніми значеннями `danceability`, `energy` або `valence`, які раніше не враховувались.
Але результат стане менш надійним статистично, бо жанри з меншою кількістю треків можуть мати випадково завищені або занижені середні значення. Поріг у 100 треків робить порівняння жанрів більш стабільним і репрезентативним.

## Частина 4 — Індекси та оптимізація

### 4.1 Compound Index для жанру та популярності

**1) Порівняння до та після створення індексу**

До створення індексу MongoDB виконувала запит через повне сканування колекції — `COLLSCAN`.
Після створення compound index з'явився `IXSCAN` в `winningPlan`.
Також змінилися ключові показники `executionStats`:
`totalDocsExamined` зменшився, `totalKeysExamined` став показувати кількість переглянутих ключів індексу, а `executionTimeMillis` став меншим.
Це означає, що запит став ефективнішим.

**2) Результати explain()**

Поточні індекси перед очищенням:

```js
[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  {
    v: 2,
    key: { track_genre: 1, popularity: -1, 'audio_features.danceability': 1 },
    name: 'idx_genre_popularity_danceability'
  }
]
```

Видаляємо всі індекси, крім `_id`.

Індекси після очищення:

```js
[
  { v: 2, key: { _id: 1 }, name: '_id_' }
]
```

Explain без індексу (є stage: `COLLSCAN` — перебір без індексу):

```js
{
  winningPlan: {
    isCached: false,
    stage: 'SORT',
    sortPattern: { popularity: -1 },
    memLimit: 33554432,
    type: 'simple',
    inputStage: {
      stage: 'COLLSCAN',
      filter: {
        '$and': [
          { track_genre: { '$eq': 'pop' } },
          { 'audio_features.danceability': { '$gte': 0.7 } }
        ]
      },
      direction: 'forward'
    }
  },
  totalDocsExamined: 113999,
  totalKeysExamined: 0,
  nReturned: 354,
  executionTimeMillis: 618
}
```

Створюємо compound index.

Індекси після створення:

```js
[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  {
    v: 2,
    key: { track_genre: 1, popularity: -1, 'audio_features.danceability': 1 },
    name: 'idx_genre_popularity_danceability'
  }
]
```

Explain після створення індексу (є stage: `IXSCAN` — використання індексу):

```js
{
  winningPlan: {
    isCached: false,
    stage: 'FETCH',
    inputStage: {
      stage: 'IXSCAN',
      keyPattern: { track_genre: 1, popularity: -1, 'audio_features.danceability': 1 },
      indexName: 'idx_genre_popularity_danceability',
      isMultiKey: false,
      multiKeyPaths: {
        track_genre: [],
        popularity: [],
        'audio_features.danceability': []
      },
      isUnique: false,
      isSparse: false,
      isPartial: false,
      indexVersion: 2,
      direction: 'forward',
      indexBounds: {
        track_genre: ['["pop", "pop"]'],
        popularity: ['[MaxKey, MinKey]'],
        'audio_features.danceability': ['[0.7, inf.0]']
      }
    }
  },
  totalDocsExamined: 354,
  totalKeysExamined: 412,
  nReturned: 354,
  executionTimeMillis: 3
}
```

### 4.2 Індекс для інших полів

Запит для пошуку музики для роботи:

```js
{
  'audio_features.instrumentalness': { '$gt': 0.5 },
  'audio_features.speechiness': { '$lt': 0.1 },
  explicit: false
}
```

Поточні індекси перед очищенням:

```js
[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  {
    v: 2,
    key: { explicit: 1, 'audio_features.instrumentalness': 1, 'audio_features.speechiness': 1 },
    name: 'idx_work_music'
  }
]
```

Видаляємо всі індекси, крім `_id`.

Індекси після очищення:

```js
[
  { v: 2, key: { _id: 1 }, name: '_id_' }
]
```

Explain без індексу:

```js
{
  winningPlan: {
    isCached: false,
    stage: 'COLLSCAN',
    filter: {
      '$and': [
        { explicit: { '$eq': false } },
        { 'audio_features.speechiness': { '$lt': 0.1 } },
        { 'audio_features.instrumentalness': { '$gt': 0.5 } }
      ]
    },
    direction: 'forward'
  },
  totalDocsExamined: 113999,
  totalKeysExamined: 0,
  nReturned: 16141,
  executionTimeMillis: 164
}
```

Створюємо compound index для музики для роботи.

Індекси після створення:

```js
[
  { v: 2, key: { _id: 1 }, name: '_id_' },
  {
    v: 2,
    key: { explicit: 1, 'audio_features.instrumentalness': 1, 'audio_features.speechiness': 1 },
    name: 'idx_work_music'
  }
]
```

Explain після створення індексу:

```js
{
  winningPlan: {
    isCached: false,
    stage: 'FETCH',
    inputStage: {
      stage: 'IXSCAN',
      keyPattern: { explicit: 1, 'audio_features.instrumentalness': 1, 'audio_features.speechiness': 1 },
      indexName: 'idx_work_music',
      isMultiKey: false,
      multiKeyPaths: {
        explicit: [],
        'audio_features.instrumentalness': [],
        'audio_features.speechiness': []
      },
      isUnique: false,
      isSparse: false,
      isPartial: false,
      indexVersion: 2,
      direction: 'forward',
      indexBounds: {
        explicit: ['[false, false]'],
        'audio_features.instrumentalness': ['(0.5, inf.0]'],
        'audio_features.speechiness': ['[-inf.0, 0.1)']
      }
    }
  },
  totalDocsExamined: 16141,
  totalKeysExamined: 16602,
  nReturned: 16141,
  executionTimeMillis: 60
}
```

### Завдання 3. Покривний запит

Він не є покривним запитом (covered query), тому що за замовчуванням MongoDB повертає всі поля документа, включно з `_id`. Створений індекс містить лише поля `track_genre`, `popularity` та `audio_features.danceability`, але не містить усіх полів документа.

Щоб запит став покривним, потрібно додати проєкцію, яка залишає тільки проіндексовані поля, і приховати `_id`, наприклад:

```js
db.tracks.find(
  {
    track_genre: "pop",
    popularity: { $gte: 70 }
  },
  {
    _id: 0,
    track_genre: 1,
    popularity: 1
  }
);
```

У такому випадку MongoDB може отримати результат лише з індексу, без звернення до самих документів.
