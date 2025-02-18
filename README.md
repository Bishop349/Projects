This repository contains 2 projects involving game development and database interaction. The projects included are:
WebsiteGame (JavaScript, Html)- A simple Game involving Dragging a Points per game Number to its Nba Player
tracking and data for website (MySQL and Php) This code gathers information from the website game and uploads its inofrmation to a MySQL database
Hangman (C#) - A simple Hangman game.

Hangman Game (C#)
Description
A simple command-line Hangman game implemented in C#. The game randomly selects a word from a predefined list, and the player must guess it letter by letter before running out of attempts.
Features
How to Run
Open a terminal or command prompt.
Compile and run using:
csc Hangman.cs
./Hangman

PHP & MySQL Score Tracker

Description

A PHP script that receives user scores and information stores them in a MySQL database.
Setup Instructions
Install XAMPP.
Place the PHP and website file in the htdocs directory.
Start Apache and MySQL from XAMPP.

SQL Database code

CREATE DATABASE game_scores;
USE game_scores;

CREATE TABLE results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    score INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

Setup Instructions
Open phpMyAdmin .
Copy and execute the script above.
Ensure the game_scores database is active before running the PHP script.

