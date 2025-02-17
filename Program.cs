using System;
using System.Linq;

class Hangman
{
    static void Main()
    {
        string[] wordList = { "php", "java", "html", "SQL", "python" };
        Random random = new Random();
        string wordToGuess = wordList[random.Next(wordList.Length)];
        char[] guessedWord = new string('_', wordToGuess.Length).ToCharArray();
        int attemptsLeft = 6;
        bool wordGuessed = false;
        string guessedLetters = "";

        Console.WriteLine("Welcome to Hangman!");
        Console.WriteLine("Try to guess the word. You have " + attemptsLeft + " incorrect attempts.");
        
        while (attemptsLeft > 0 && !wordGuessed)
        {
            Console.WriteLine("\nWord: " + new string(guessedWord));
            Console.WriteLine("Guessed Letters: " + guessedLetters);
            Console.Write("Enter a letter: ");
            char guess = Console.ReadLine().ToLower().FirstOrDefault();

            if (!char.IsLetter(guess))
            {
                Console.WriteLine("Invalid input. Please enter a letter.");
                continue;
            }

            if (guessedLetters.Contains(guess))
            {
                Console.WriteLine("You already guessed that letter!");
                continue;
            }

            guessedLetters += guess + " ";

            if (wordToGuess.Contains(guess))
            {
                for (int i = 0; i < wordToGuess.Length; i++)
                {
                    if (wordToGuess[i] == guess)
                    {
                        guessedWord[i] = guess;
                    }
                }
                Console.WriteLine("Correct!");
            }
            else
            {
                attemptsLeft--;
                Console.WriteLine($"Wrong! Attempts left: {attemptsLeft}");
            }

            wordGuessed = !new string(guessedWord).Contains('_');
        }

        if (wordGuessed)
        {
            Console.WriteLine("\n Congratulations! You guessed the word: " + wordToGuess);
        }
        else
        {
            Console.WriteLine("\n Game Over! The correct word was: " + wordToGuess);
        }
    }
}

