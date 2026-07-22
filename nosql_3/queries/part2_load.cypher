// 1. Користувачі

LOAD CSV WITH HEADERS
FROM 'file:///users.csv' AS row

MERGE (u:User {userId: toInteger(row.userId)})
SET u.gender = row.gender,
    u.age = toInteger(row.age),
    u.occupation = toInteger(row.occupation);


// 2. Фільми

LOAD CSV WITH HEADERS
FROM 'file:///movies.csv' AS row

MERGE (m:Movie {movieId: toInteger(row.movieId)})
SET m.title = trim(
        replace(
            row.title,
            '(' + substring(row.title, size(row.title) - 5, 4) + ')',
            ''
        )
    ),
    m.year = toInteger(
        substring(row.title, size(row.title) - 5, 4)
    );


// 3. Жанри

LOAD CSV WITH HEADERS
FROM 'file:///movies.csv' AS row

UNWIND split(row.genres, '|') AS genreName

MERGE (:Genre {name: genreName});


// 4. Індекси для прискорення пошуку вузлів

CREATE INDEX user_id_index IF NOT EXISTS
FOR (u:User)
ON (u.userId);

CREATE INDEX movie_id_index IF NOT EXISTS
FOR (m:Movie)
ON (m.movieId);

CREATE INDEX genre_name_index IF NOT EXISTS
FOR (g:Genre)
ON (g.name);

// Очікуємо завершення створення індексів
CALL db.awaitIndexes();


// 5. Зв’язки Movie -> Genre

LOAD CSV WITH HEADERS
FROM 'file:///movies.csv' AS row

UNWIND split(row.genres, '|') AS genreName

MATCH (m:Movie {movieId: toInteger(row.movieId)})
MATCH (g:Genre {name: genreName})

MERGE (m)-[:HAS_GENRE]->(g);


// 6. Зв’язки User -> Movie з оцінками

CALL apoc.periodic.iterate(
    "
    LOAD CSV WITH HEADERS
    FROM 'file:///ratings.csv' AS row
    RETURN row
    ",
    "
    MATCH (u:User {userId: toInteger(row.userId)})
    MATCH (m:Movie {movieId: toInteger(row.movieId)})

    MERGE (u)-[r:RATED]->(m)
    SET r.rating = toFloat(row.rating),
        r.timestamp = toInteger(row.timestamp)
    ",
    {
        batchSize: 10000,
        parallel: false
    }
);