print("========================================");
print("Завдання 1. Топ-10 виконавців за середньою популярністю");
print("========================================");

db = db.getSiblingDB("spotify");
db.tracks
  .aggregate([
    {
      $unwind: "$artists",
    },
    {
      $group: {
        _id: "$artists",
        track_count: { $sum: 1 },
        avg_popularity_raw: { $avg: "$popularity" },
      },
    },
    {
      $match: {
        track_count: { $gte: 5 },
      },
    },
    {
      $project: {
        _id: 0,
        artist: "$_id",
        track_count: 1,
        avg_popularity: {
          $round: ["$avg_popularity_raw", 1],
        },
      },
    },
    {
      $sort: {
        avg_popularity: -1,
        track_count: -1,
      },
    },
    {
      $limit: 10,
    },
  ])
  .forEach((result) => printjson(result));

print("==========================================");
print("Завдання 2. Розподіл треків за настроєм");
print("==========================================");

db.tracks
  .aggregate([
    {
      $addFields: {
        mood: {
          $switch: {
            branches: [
              {
                case: {
                  $and: [
                    { $gte: ["$audio_features.valence", 0.5] },
                    { $gte: ["$audio_features.energy", 0.5] },
                  ],
                },
                then: "happy",
              },
              {
                case: {
                  $and: [
                    { $lt: ["$audio_features.valence", 0.5] },
                    { $gte: ["$audio_features.energy", 0.5] },
                  ],
                },
                then: "angry",
              },
              {
                case: {
                  $and: [
                    { $gte: ["$audio_features.valence", 0.5] },
                    { $lt: ["$audio_features.energy", 0.5] },
                  ],
                },
                then: "calm",
              },
              {
                case: {
                  $and: [
                    { $lt: ["$audio_features.valence", 0.5] },
                    { $lt: ["$audio_features.energy", 0.5] },
                  ],
                },
                then: "sad",
              },
            ],
            default: "unknown",
          },
        },
      },
    },
    {
      $group: {
        _id: "$mood",
        track_count: { $sum: 1 },
      },
    },
    {
      $project: {
        _id: 0,
        mood: "$_id",
        track_count: 1,
      },
    },
    {
      $sort: {
        track_count: -1,
      },
    },
  ])
  .forEach(printjson);

print("==========================================");
print("Завдання 3. Найбільш танцювальний жанр");
print("==========================================");

db.tracks
  .aggregate([
    {
      $group: {
        _id: "$track_genre",
        track_count: { $sum: 1 },
        avg_danceability: { $avg: "$audio_features.danceability" },
        avg_energy: { $avg: "$audio_features.energy" },
        avg_valence: { $avg: "$audio_features.valence" },
      },
    },
    {
      $match: {
        track_count: { $gte: 100 },
      },
    },
    {
      $project: {
        _id: 0,
        genre: "$_id",
        avg_danceability: { $round: ["$avg_danceability", 3] },
        avg_energy: { $round: ["$avg_energy", 3] },
        avg_valence: { $round: ["$avg_valence", 3] },
        track_count: 1,
      },
    },
    {
      $sort: {
        avg_danceability: -1,
      },
    },
    {
      $limit: 1,
    },
  ])
  .forEach(printjson);
