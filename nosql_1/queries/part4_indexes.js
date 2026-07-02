// // part4_indexes.js
// // Запуск:
// // mongosh "ВАШ_URI" --file part4_indexes.js

 db = db.getSiblingDB("spotify");

// print("==========================================");
// print("Завдання 1. Аналіз запиту та індексація");
// print("==========================================");

// const query = {
//   track_genre: "pop",
//   "audio_features.danceability": { $gte: 0.7 }
// };

// const sortOrder = {
//   popularity: -1
// };

// print("\nПоточні індекси перед очищенням:");
// printjson(db.tracks.getIndexes());

// print("\nВидаляємо всі індекси, крім _id:");
// db.tracks.dropIndexes();

// print("\nІндекси після очищення:");
// printjson(db.tracks.getIndexes());

// print("\n--- Explain без індексу ---");

// const explainWithoutIndex = db.tracks
//   .find(query)
//   .sort(sortOrder)
//   .explain("executionStats");

// printjson({
//   winningPlan: explainWithoutIndex.queryPlanner.winningPlan,
//   totalDocsExamined: explainWithoutIndex.executionStats.totalDocsExamined,
//   totalKeysExamined: explainWithoutIndex.executionStats.totalKeysExamined,
//   nReturned: explainWithoutIndex.executionStats.nReturned,
//   executionTimeMillis: explainWithoutIndex.executionStats.executionTimeMillis
// });

// print("\nСтворюємо compound index:");

// db.tracks.createIndex(
//   {
//     track_genre: 1,
//     popularity: -1,
//     "audio_features.danceability": 1
//   },
//   {
//     name: "idx_genre_popularity_danceability"
//   }
// );

// print("\nІндекси після створення:");
// printjson(db.tracks.getIndexes());

// print("\n--- Explain після створення індексу ---");

// const explainWithIndex = db.tracks
//   .find(query)
//   .sort(sortOrder)
//   .explain("executionStats");

// printjson({
//   winningPlan: explainWithIndex.queryPlanner.winningPlan,
//   totalDocsExamined: explainWithIndex.executionStats.totalDocsExamined,
//   totalKeysExamined: explainWithIndex.executionStats.totalKeysExamined,
//   nReturned: explainWithIndex.executionStats.nReturned,
//   executionTimeMillis: explainWithIndex.executionStats.executionTimeMillis
// });

// print("\n--- Результати запиту ---");

// db.tracks
//   .find(query)
//   .sort(sortOrder)
//   .limit(10)
//   .forEach(doc => printjson(doc));


print("==========================================");
print("Завдання 2. Індекс для інших полів");
print("==========================================");

const workMusicQuery = {
  "audio_features.instrumentalness": { $gt: 0.5 },
  "audio_features.speechiness": { $lt: 0.1 },
  explicit: false
};

print("\nЗапит для пошуку музики для роботи:");
printjson(workMusicQuery);

print("\nПоточні індекси перед очищенням:");
printjson(db.tracks.getIndexes());

print("\nВидаляємо всі індекси, крім _id:");
db.tracks.dropIndexes();

print("\nІндекси після очищення:");
printjson(db.tracks.getIndexes());

print("\n--- Explain без індексу ---");

const explainWorkWithoutIndex = db.tracks
  .find(workMusicQuery)
  .explain("executionStats");

printjson({
  winningPlan: explainWorkWithoutIndex.queryPlanner.winningPlan,
  totalDocsExamined: explainWorkWithoutIndex.executionStats.totalDocsExamined,
  totalKeysExamined: explainWorkWithoutIndex.executionStats.totalKeysExamined,
  nReturned: explainWorkWithoutIndex.executionStats.nReturned,
  executionTimeMillis: explainWorkWithoutIndex.executionStats.executionTimeMillis
});

print("\nСтворюємо compound index для музики для роботи:");

db.tracks.createIndex(
  {
    explicit: 1,
    "audio_features.instrumentalness": 1,
    "audio_features.speechiness": 1
  },
  {
    name: "idx_work_music"
  }
);

print("\nІндекси після створення:");
printjson(db.tracks.getIndexes());

print("\n--- Explain після створення індексу ---");

const explainWorkWithIndex = db.tracks
  .find(workMusicQuery)
  .explain("executionStats");

printjson({
  winningPlan: explainWorkWithIndex.queryPlanner.winningPlan,
  totalDocsExamined: explainWorkWithIndex.executionStats.totalDocsExamined,
  totalKeysExamined: explainWorkWithIndex.executionStats.totalKeysExamined,
  nReturned: explainWorkWithIndex.executionStats.nReturned,
  executionTimeMillis: explainWorkWithIndex.executionStats.executionTimeMillis
});

print("\n--- Приклади результатів запиту ---");

db.tracks
  .find(
    workMusicQuery,
    {
      _id: 0,
      track_name: 1,
      artists: 1,
      explicit: 1,
      "audio_features.instrumentalness": 1,
      "audio_features.speechiness": 1
    }
  )
  .limit(10)
  .forEach(doc => printjson(doc));  