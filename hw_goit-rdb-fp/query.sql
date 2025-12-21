SELECT COUNT(*) FROM infectious_cases;
SELECT * FROM infectious_cases;

CREATE TABLE infectious_entities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    entity VARCHAR(255) NOT NULL,
    code   VARCHAR(10)  NOT NULL,
    UNIQUE KEY uk_entity_code (entity, code)
);

INSERT INTO infectious_entities (entity, code)
SELECT DISTINCT Entity, Code
FROM infectious_cases;

select * from infectious_entities;

CREATE TABLE infectious_cases_norm (
    id INT PRIMARY KEY AUTO_INCREMENT,
    entity_id INT NOT NULL,
    Year INT NOT NULL,
    Number_yaws        DECIMAL(15,4),
    polio_cases        DECIMAL(15,4),
    cases_guinea_worm  DECIMAL(15,4),
    Number_rabies      DECIMAL(15,4),
    -- если есть еще показатели – добавь сюда

    FOREIGN KEY (entity_id) REFERENCES infectious_entities(id)
);

INSERT INTO infectious_cases_norm (
    entity_id,
    Year,
    Number_yaws,
    polio_cases,
    cases_guinea_worm,
    Number_rabies
)
SELECT 
    e.id,
    c.Year,
    NULLIF(c.Number_yaws, ''),
    NULLIF(c.polio_cases, ''),
    NULLIF(c.cases_guinea_worm, ''),
    NULLIF(c.Number_rabies, '')
FROM infectious_cases c
JOIN infectious_entities e
  ON e.entity = c.EntityNumber_yaws
 AND e.code   = c.Code;

select count(*) from infectious_cases_norm ;

SELECT 
    e.id          AS entity_id,
    e.entity      AS Entity,
    e.code        AS Code,
    AVG(ic.Number_rabies) AS avg_rabies,
    MIN(ic.Number_rabies) AS min_rabies,
    MAX(ic.Number_rabies) AS max_rabies,
    SUM(ic.Number_rabies) AS sum_rabies
FROM infectious_cases_norm ic
JOIN infectious_entities e
  ON ic.entity_id = e.id
GROUP BY e.id, e.entity, e.code
ORDER BY e.entity, e.code;

SELECT 
    e.id          AS entity_id,
    e.entity      AS Entity,
    e.code        AS Code,
    AVG(ic.Number_rabies) AS avg_rabies,
    MIN(ic.Number_rabies) AS min_rabies,
    MAX(ic.Number_rabies) AS max_rabies,
    SUM(ic.Number_rabies) AS sum_rabies
FROM infectious_cases_norm ic
JOIN infectious_entities e
  ON ic.entity_id = e.id
GROUP BY e.id, e.entity, e.code
ORDER BY avg_rabies desc
LIMIT 10;

SELECT 
    year,
    
    -- 1) 1 січня відповідного року
    STR_TO_DATE(CONCAT(year, '-01-01'), '%Y-%m-%d') AS first_january,
    
    -- 2) поточна дата
    CURRENT_DATE() AS today,
    
    -- 3) різниця в роках
    TIMESTAMPDIFF(YEAR, 
        STR_TO_DATE(CONCAT(year, '-01-01'), '%Y-%m-%d'),
        CURRENT_DATE()
    ) AS diff_years
    
FROM pandemic.infectious_cases_norm;

DROP FUNCTION IF EXISTS years_difference;
DELIMITER $$

CREATE FUNCTION years_difference(input_year INT)
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE first_january DATE;
    SET first_january = STR_TO_DATE(CONCAT(input_year, '-01-01'), '%Y-%m-%d');

    RETURN TIMESTAMPDIFF(YEAR, first_january, CURRENT_DATE());
END$$

DELIMITER ;

SELECT 
    year,
    STR_TO_DATE(CONCAT(year, '-01-01'), '%Y-%m-%d') AS first_january,
    CURRENT_DATE() AS today,
    years_difference(year)  AS diff_years
FROM pandemic.infectious_cases_norm;
