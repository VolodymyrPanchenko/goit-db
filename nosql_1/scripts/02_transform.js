// scripts/02_transform.js
// Запуск: mongosh "ВАШ_URI" --file scripts/02_transform.js

// 1. Використовуємо базу spotify
db = db.getSiblingDB("spotify");

// Перед трансформацією видаляємо стару колекцію tracks, якщо вона існує
db.tracks.drop();

// 2-5. Трансформація tracks_raw -> tracks
db.tracks_raw.aggregate([
  {
    $project: {
      _id: 0,

      // Основні поля для аналізу
      track_id: 1,
      track_name: 1,
      album_name: 1,
      explicit: 1,
      popularity: 1,
      duration_ms: 1,
      track_genre: 1,

      // 3. Перетворення артистів:
      // рядок "Artist 1; Artist 2" -> масив ["Artist 1", "Artist 2"]
      artists: {
        $filter: {
          input: {
            $map: {
              input: { $split: ["$artists", ";"] },
              as: "artist",
              in: { $trim: { input: "$$artist" } },
            },
          },
          as: "artist",
          cond: { $ne: ["$$artist", ""] },
        },
      },

      // 4. Вкладений об'єкт audio_features
      audio_features: {
        danceability: "$danceability",
        energy: "$energy",
        loudness: "$loudness",
        speechiness: "$speechiness",
        acousticness: "$acousticness",
        instrumentalness: "$instrumentalness",
        liveness: "$liveness",
        valence: "$valence",
        tempo: "$tempo",
        key: "$key",
        mode: "$mode",
        time_signature: "$time_signature",
      },

      // Тривалість у секундах, округлена до одного знака
      duration_sec: {
        $round: [{ $divide: ["$duration_ms", 1000] }, 1],
      },

      // Рівень популярності
      popularity_tier: {
        $switch: {
          branches: [
            {
              case: { $gte: ["$popularity", 70] },
              then: "high",
            },
            {
              case: {
                $and: [
                  { $gte: ["$popularity", 40] },
                  { $lt: ["$popularity", 70] },
                ],
              },
              then: "medium",
            },
          ],
          default: "low",
        },
      },
    },
  },
  {
    // Створюємо нову колекцію tracks
    $out: "tracks",
  },
]);

print("Колекцію tracks створено успішно.");
print("Кількість документів у tracks:");
print(db.tracks.countDocuments());

print("Приклад документа:");
printjson(db.tracks.findOne());
