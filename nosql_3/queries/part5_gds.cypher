// =====================================================
// 5.1. PageRank на графі фільмів
// =====================================================


// Крок 1. Створюємо зв’язки між фільмами,
// які ті самі користувачі оцінили високо

MATCH (m1:Movie)<-[r1:RATED]-(u:User)-[r2:RATED]->(m2:Movie)
WHERE r1.rating >= 4
  AND r2.rating >= 4
  AND id(m1) < id(m2)

WITH
  m1,
  m2,
  count(u) AS weight

// Залишаємо фільми, які мають більше ніж 20 оцінок

WHERE size([(m1)<-[:RATED]-() | 1]) > 20
  AND size([(m2)<-[:RATED]-() | 1]) > 20

WITH m1, m2, weight
ORDER BY weight DESC
LIMIT 50000

MERGE (m1)-[co:CO_RATED]-(m2)
SET co.weight = weight;


// Крок 2. Створюємо проєкцію графа в пам’яті GDS

CALL gds.graph.project(
  'movieGraph',
  'Movie',
  {
    CO_RATED: {
      orientation: 'UNDIRECTED',
      properties: 'weight'
    }
  }
)
YIELD
  graphName,
  nodeCount,
  relationshipCount

RETURN
  graphName,
  nodeCount,
  relationshipCount;


// Крок 3. Запускаємо PageRank

CALL gds.pageRank.stream(
  'movieGraph',
  {
    relationshipWeightProperty: 'weight'
  }
)
YIELD nodeId, score

WITH
  gds.util.asNode(nodeId) AS movie,
  score

RETURN
  movie.movieId AS movieId,
  movie.title AS title,
  movie.year AS year,
  round(score, 4) AS pageRank

ORDER BY pageRank DESC
LIMIT 20;


// Візуалізація зв’язків між фільмами
// з найвищим значенням PageRank

CALL gds.pageRank.stream(
  'movieGraph',
  {
    relationshipWeightProperty: 'weight'
  }
)
YIELD nodeId, score

WITH
  gds.util.asNode(nodeId) AS movie,
  score

ORDER BY score DESC
LIMIT 10

WITH collect(movie) AS topMovies

UNWIND topMovies AS m1

MATCH path = (m1)-[:CO_RATED]-(m2:Movie)
WHERE m2 IN topMovies

RETURN path
LIMIT 100;


// Крок 4. Видаляємо проєкцію з оперативної пам’яті GDS

CALL gds.graph.drop('movieGraph')
YIELD graphName

RETURN graphName;


// Видаляємо тимчасові ребра CO_RATED з бази Neo4j

MATCH ()-[co:CO_RATED]-()
DELETE co;


// =====================================================
// 5.2. Виявлення спільнот користувачів за допомогою Louvain
// =====================================================


// Крок 1. Пакетно матеріалізуємо зв’язки між користувачами,
// які поставили оцінку 5 однаковим фільмам

CALL apoc.periodic.iterate(
  "
  MATCH (u1:User)
  RETURN u1
  ",
  "
  MATCH (u1)-[r1:RATED]->(m:Movie)<-[r2:RATED]-(u2:User)
  WHERE r1.rating = 5
    AND r2.rating = 5
    AND id(u1) < id(u2)

  WITH
    u1,
    u2,
    count(m) AS weight

  WHERE weight >= 2

  WITH u1, u2, weight
  ORDER BY weight DESC
  LIMIT 10

  MERGE (u1)-[sim:SIMILAR]-(u2)
  SET sim.weight = weight
  ",
  {
    batchSize: 1,
    parallel: false
  }
)
YIELD
  batches,
  total,
  failedBatches,
  errorMessages

RETURN
  batches,
  total,
  failedBatches,
  errorMessages;


// Крок 2. Створюємо проєкцію графа користувачів
// у пам’яті GDS

CALL gds.graph.project(
  'userSimilarity',
  'User',
  {
    SIMILAR: {
      orientation: 'UNDIRECTED',
      properties: 'weight'
    }
  }
)
YIELD
  graphName,
  nodeCount,
  relationshipCount

RETURN
  graphName,
  nodeCount,
  relationshipCount;


// Крок 3. Запускаємо алгоритм Louvain і записуємо
// ідентифікатор спільноти у властивість communityId

CALL gds.louvain.write(
  'userSimilarity',
  {
    relationshipWeightProperty: 'weight',
    writeProperty: 'communityId'
  }
)
YIELD
  communityCount,
  modularity,
  modularities,
  ranLevels

RETURN
  communityCount,
  round(modularity, 4) AS modularity,
  modularities,
  ranLevels;


// Крок 4.1. Виводимо 10 найбільших спільнот

MATCH (u:User)
WHERE u.communityId IS NOT NULL

WITH
  u.communityId AS communityId,
  count(u) AS userCount

RETURN
  communityId,
  userCount

ORDER BY userCount DESC
LIMIT 10;


// Крок 4.2. Визначаємо три найпопулярніші жанри
// для кожної знайденої спільноти

MATCH (u:User)
WHERE u.communityId IS NOT NULL

WITH
  u.communityId AS communityId,
  count(u) AS communitySize

MATCH (member:User)-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE member.communityId = communityId
  AND r.rating >= 4

WITH
  communityId,
  communitySize,
  g.name AS genre,
  count(r) AS highRatingsCount

ORDER BY
  communityId,
  highRatingsCount DESC

WITH
  communityId,
  communitySize,
  collect({
    genre: genre,
    highRatingsCount: highRatingsCount
  })[0..3] AS topGenres

RETURN
  communityId,
  communitySize,
  topGenres

ORDER BY communitySize DESC;


// Візуалізація найбільшої спільноти Louvain

MATCH (u:User)
WHERE u.communityId IS NOT NULL

WITH
  u.communityId AS communityId,
  count(u) AS communitySize

ORDER BY communitySize DESC
LIMIT 1

MATCH path = (u1:User)-[:SIMILAR]-(u2:User)
WHERE u1.communityId = communityId
  AND u2.communityId = communityId

RETURN path
LIMIT 100;


// =====================================================
// 5.3. Найкоротші шляхи між користувачами
// =====================================================


// Крок 1. Видаляємо проєкцію Louvain,
// але залишаємо ребра SIMILAR для алгоритму Дейкстри

CALL gds.graph.drop('userSimilarity', false)
YIELD graphName

RETURN graphName;


// Крок 2. Перетворюємо силу схожості на відстань.
//
// Більше значення weight означає сильнішу схожість.
// Оскільки Дейкстра шукає мінімальну вартість,
// використовуємо обернене значення.

MATCH ()-[sim:SIMILAR]-()
SET sim.distance = 1.0 / toFloat(sim.weight);


// Видаляємо стару проєкцію, якщо вона існує

CALL gds.graph.drop('userGraph', false)
YIELD graphName

RETURN graphName;


// Крок 3. Створюємо проєкцію для Дейкстри

CALL gds.graph.project(
  'userGraph',
  'User',
  {
    SIMILAR: {
      orientation: 'UNDIRECTED',
      properties: ['weight', 'distance']
    }
  }
)
YIELD
  graphName,
  nodeCount,
  relationshipCount

RETURN
  graphName,
  nodeCount,
  relationshipCount;


// Крок 4. Вибираємо до десяти пар користувачів
// і знаходимо найкоротший шлях для кожної пари

MATCH (u:User)
WHERE u.communityId IS NOT NULL

WITH
  u.communityId AS communityId,
  collect(u) AS members

WHERE size(members) >= 2

WITH
  communityId,
  members[0] AS source,
  members[-1] AS target

LIMIT 10

CALL gds.shortestPath.dijkstra.stream(
  'userGraph',
  {
    sourceNode: source,
    targetNode: target,
    relationshipWeightProperty: 'distance'
  }
)
YIELD
  totalCost,
  nodeIds

WITH collect({
  communityId: communityId,
  sourceUserId: source.userId,
  targetUserId: target.userId,
  pathLength: size(nodeIds) - 1,
  intermediateUsers: size(nodeIds) - 2,
  totalDistance: round(totalCost, 4)
}) AS results

RETURN
  results,

  round(
    reduce(
      total = 0.0,
      result IN results | total + result.pathLength
    ) / size(results),
    2
  ) AS averagePathLength;


// Візуалізація одного найкоротшого шляху

MATCH (u:User)
WHERE u.communityId IS NOT NULL

WITH
  u.communityId AS communityId,
  collect(u) AS members

WHERE size(members) >= 2

WITH
  members[0] AS source,
  members[-1] AS target

LIMIT 1

CALL gds.shortestPath.dijkstra.stream(
  'userGraph',
  {
    sourceNode: source,
    targetNode: target,
    relationshipWeightProperty: 'distance'
  }
)
YIELD path

RETURN path;


// Крок 5. Видаляємо проєкцію після завершення аналізу

CALL gds.graph.drop('userGraph', false)
YIELD graphName

RETURN graphName;


// Крок 6. Видаляємо тимчасові ребра SIMILAR

MATCH ()-[sim:SIMILAR]-()
DELETE sim;