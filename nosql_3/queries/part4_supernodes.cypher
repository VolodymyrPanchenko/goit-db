//Завдання

//Крок 1. Знайдіть вузли з аномально великою кількістю ребер:
// Крок 1. Вузли з найбільшою кількістю ребер

MATCH (n)-[r]-()
WITH n, count(r) AS degree
RETURN
    labels(n) AS nodeLabels,
    CASE
        WHEN n:User THEN toString(n.userId)
        WHEN n:Movie THEN n.title
        WHEN n:Genre THEN n.name
        ELSE toString(id(n))
    END AS node,
    degree
ORDER BY degree DESC
LIMIT 20;   

// Визначаємо жанрові супервузли:
// підраховуємо кількість фільмів, пов’язаних із кожним жанром

MATCH (g:Genre)-[r:HAS_GENRE]-(:Movie)
RETURN
  g.name AS genre,
  count(r) AS movieCount
ORDER BY movieCount DESC;