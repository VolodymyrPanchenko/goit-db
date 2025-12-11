CREATE SCHEMA IF NOT EXISTS LibraryManagement;
USE LibraryManagement;

CREATE TABLE authors (
    author_id INT AUTO_INCREMENT PRIMARY KEY,
    author_name VARCHAR(255) NOT NULL
);
-- 2️⃣ Додавання мок-даних
INSERT INTO authors (author_name) VALUES
('Stephen King'),
('J. K. Rowling');
CREATE TABLE genres (
    genre_id INT NOT NULL AUTO_INCREMENT,
    genre_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (genre_id)
);

INSERT INTO genres (genre_name) VALUES
('Fantasy'),
('Horror'),
('Science Fiction'),
('Detective'),
('Drama');

CREATE TABLE books (
    book_id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    publication_year YEAR,
    author_id INT,
    genre_id INT,
    PRIMARY KEY (book_id),
    FOREIGN KEY (author_id) REFERENCES authors(author_id),
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id));
    
INSERT INTO books (title, publication_year, author_id, genre_id) VALUES
('The Shining', 1977, 1, 2),
('Carrie', 1974, 1, 2),
('Harry Potter and the Philosopher''s Stone', 1997, 2, 1),
('Harry Potter and the Chamber of Secrets', 1998, 2, 1);

 
 CREATE TABLE users (
    user_id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    PRIMARY KEY (user_id)
);

INSERT INTO users (username, email) VALUES
('john_doe', 'john@example.com'),
('maria_smith', 'maria.smith@example.com'),
('peter_pan', 'peter.pan@example.com');

CREATE TABLE borrowed_books (
    borrow_id INT NOT NULL AUTO_INCREMENT,
    book_id INT,
    user_id INT,
    borrow_date DATE,
    return_date DATE,
    PRIMARY KEY (borrow_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

INSERT INTO borrowed_books (book_id, user_id, borrow_date, return_date) VALUES
(1, 1, '2025-01-10', '2025-01-20'),
(3, 2, '2025-02-05', '2025-02-18'),
(2, 3, '2025-03-01', NULL); -- книга ще не повернута
