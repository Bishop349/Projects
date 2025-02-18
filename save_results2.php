<?php
// Database connection
$servername = "localhost";
$username = "root"; // Default XAMPP MySQL user
$password = ""; // No password by default
$dbname = "game_scores"; // Ensure this matches your created database

$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Get user data from the AJAX request
$userId = $_POST['userId'];
$score = $_POST['score'];

// Insert into MySQL database
$sql = "INSERT INTO results (user_id, score) VALUES ('$userId', '$score')";

if ($conn->query($sql) === TRUE) {
    echo "New record created successfully";
} else {
    echo "Error: " . $sql . "<br>" . $conn->error;
}

$conn->close();
?>
