// queries/part2_queries.js
// Запуск:
// mongosh "ВАШ_URI" --file queries/part2_queries.js

db = db.getSiblingDB("spotify");

print("========================================");
print("Завдання 1. Треки для вечірки");
print("========================================");

const partyTracksQuery = {
  "audio_features.danceability": { $gt: 0.7 },
  "audio_features.energy": { $gt: 0.7 },
  duration_ms: { $gte: 180000, $lte: 300000 }
};

const partyTracksProjection = {
  _id: 0,
  track_name: 1,
  artists: 1,
  track_genre: 1,
  duration_ms: 1,
  popularity: 1,
  "audio_features.danceability": 1,
  "audio_features.energy": 1
};

const partyTracksCount = db.tracks.countDocuments(partyTracksQuery);

print("Кількість знайдених треків:");
print(partyTracksCount);

db.tracks
  .find(partyTracksQuery, partyTracksProjection)
  .sort({ popularity: -1 })
  .limit(20)
  .forEach(track => printjson(track));

print("========================================");
print("Завдання 2. Виконавці, у яких усі треки популярні");
print("========================================");

const popularArtists = db.tracks.aggregate([
  {
    $unwind: "$artists"
  },
  {
    $group: {
      _id: "$artists",
      track_count: { $sum: 1 },
      min_popularity: { $min: "$popularity" },
      avg_popularity_raw: { $avg: "$popularity" }
    }
  },
  {
    $match: {
      track_count: { $gte: 3 },
      min_popularity: { $gte: 60 }
    }
  },
  {
    $project: {
      _id: 0,
      artist: "$_id",
      track_count: 1,
      min_popularity: {
        $round: ["$min_popularity", 1]
      },
      avg_popularity: {
        $round: ["$avg_popularity_raw", 1]
      }
    }
  },
  {
    $sort: {
      avg_popularity: -1,
      min_popularity: -1,
      track_count: -1
    }
  },
  {
    $limit: 20
  }
]).toArray();

popularArtists.forEach(artist => printjson(artist));
print("Кількість знайдених артистів у топ-20:");
print(popularArtists.length);

print("========================================");
print("Завдання 3. Нетипові треки");
print("========================================");

const outlierGenres = db.tracks
  .aggregate([
    {
      $group: {
        _id: "$track_genre",

        avg_tempo_raw: {
          $avg: "$audio_features.tempo",
        },

        std_dev_tempo: {
          $stdDevPop: "$audio_features.tempo",
        },

        tracks: {
          $push: {
            _id: "$_id",
            track_name: "$track_name",
            popularity: "$popularity",
            artists: "$artists",
            audio_features: {
              tempo: "$audio_features.tempo",
            },
          },
        },
      },
    },
    {
      $addFields: {
        genre: "$_id",
        outlier_threshold_raw: {
          $add: ["$avg_tempo_raw", { $multiply: [2, "$std_dev_tempo"] }],
        },
      },
    },
    {
      $project: {
        _id: 0,
        genre: 1,

        avg_tempo: {
          $round: ["$avg_tempo_raw", 1],
        },

        outlier_threshold: {
          $round: ["$outlier_threshold_raw", 1],
        },

        outlier_tracks: {
          $filter: {
            input: "$tracks",
            as: "track",
            cond: {
              $gt: ["$$track.audio_features.tempo", "$outlier_threshold_raw"],
            },
          },
        },
      },
    },
    {
      $match: {
        "outlier_tracks.0": { $exists: true },
      },
    },
    {
      $sort: {
        genre: 1,
      },
    },
  ])
  .toArray();

print("Кількість жанрів з нетиповими треками:");
print(outlierGenres.length);

let outlierTracksTotal = 0;

outlierGenres.forEach((genreResult) => {
  outlierTracksTotal += genreResult.outlier_tracks.length;
});


outlierGenres.forEach(result => printjson(result));
print("Загальна кількість нетипових треків:");
print(outlierTracksTotal);

print("========================================");
print("Завдання 4. Треки для фонової роботи");
print("========================================");

const backgroundWorkQuery = {
  "audio_features.loudness": { $lt: -10 },
  "audio_features.speechiness": { $lt: 0.1 },
  "audio_features.instrumentalness": { $gt: 0.5 },
  explicit: false
};

const backgroundWorkProjection = {
  _id: 0,
  track_name: 1,
  artists: 1,
  album_name: 1,
  track_genre: 1,
  popularity: 1,
  duration_ms: 1,
  duration_sec: 1,
  explicit: 1,
  "audio_features.loudness": 1,
  "audio_features.speechiness": 1,
  "audio_features.instrumentalness": 1
};

const backgroundWorkCount = db.tracks.countDocuments(backgroundWorkQuery);

db.tracks
  .find(backgroundWorkQuery, backgroundWorkProjection)
  .sort({ popularity: -1 })
  .limit(20)
  .forEach(track => printjson(track));

print("Кількість знайдених треків:");
print(backgroundWorkCount);