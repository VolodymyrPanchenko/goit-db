//Запит 1. Знайти всі фільми жанру «Thriller» із середнім рейтингом вище 4.0:
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre {name: 'Thriller'})
MATCH (:User)-[r:RATED]->(m)
WITH m, avg(r.rating) AS averageRating
WHERE averageRating > 4.0
RETURN
    m.movieId AS movieId,
    m.title AS title,
    m.year AS year,
    round(averageRating, 2) AS averageRating
ORDER BY averageRating DESC, title;

//Запит 2. Знайти користувачів, які поставили оцінку 5 більш ніж 50 фільмам:
MATCH (u:User)-[r:RATED]->(m:Movie)
WHERE r.rating = 5.0
WITH u, count(m) AS moviesRatedFive
WHERE moviesRatedFive > 50
RETURN
    u.userId AS userId,
    u.gender AS gender,
    u.age AS age,
    u.occupation AS occupation,
    moviesRatedFive
ORDER BY moviesRatedFive DESC;

//Запит 3. Знайти фільми, які обидва користувачі (наприклад, userId=1 і userId=2) оцінили високо (рейтинг ≥ 4):
MATCH (u1:User {userId: 1})-[r1:RATED]->(m:Movie)
MATCH (u2:User {userId: 2})-[r2:RATED]->(m)
WHERE r1.rating >= 4.0
  AND r2.rating >= 4.0
RETURN
    m.movieId AS movieId,
    m.title AS title,
    m.year AS year,
    r1.rating AS user1Rating,
    r2.rating AS user2Rating
ORDER BY title;

// Запит 4. Обчислити середній рейтинг і кількість оцінок для кожного жанру
MATCH (:User)-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH
    g,
    avg(r.rating) AS averageRating,
    count(r) AS ratingsCount
RETURN
    g.name AS genre,
    round(averageRating, 2) AS averageRating,
    ratingsCount
ORDER BY averageRating DESC, ratingsCount DESC;

//Запит 5. Рекомендація «користувачі зі схожими смаками також дивилися»:
// для заданого користувача знайти фільми, які він ще не дивився, але високо оцінили користувачі з подібними смаками:
 MATCH (target:User {userId: 1})-[tr:RATED]->(commonMovie:Movie)
MATCH (similar:User)-[sr:RATED]->(commonMovie)
WHERE similar <> target
  AND tr.rating >= 4.0
  AND sr.rating >= 4.0

WITH target, similar,
     count(DISTINCT commonMovie) AS commonHighRatedMovies
WHERE commonHighRatedMovies >= 3

MATCH (similar)-[rr:RATED]->(recommended:Movie)
WHERE rr.rating >= 4.0
  AND NOT EXISTS {
      MATCH (target)-[:RATED]->(recommended)
  }

WITH
    recommended,
    avg(rr.rating) AS averageRating,
    count(DISTINCT similar) AS similarUsersCount,
    sum(commonHighRatedMovies) AS recommendationScore

RETURN
    recommended.movieId AS movieId,
    recommended.title AS title,
    recommended.year AS year,
    round(averageRating, 2) AS averageRating,
    similarUsersCount,
    recommendationScore
ORDER BY
    recommendationScore DESC,
    averageRating DESC
LIMIT 20;

//Запит 6. Знайти найкоротший ланцюжок зв’язку між двома користувачами
//через спільні фільми:
MATCH (u1:User {userId: 1}),
      (u2:User {userId: 2})

MATCH path = shortestPath(
    (u1)-[:RATED*..10]-(u2)
)

RETURN
    length(path) AS pathLength,
    [node IN nodes(path) |
        CASE
            WHEN node:User THEN 'User ' + toString(node.userId)
            WHEN node:Movie THEN node.title
        END
    ] AS connectionChain;



 
