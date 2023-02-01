# Finance
**NOTE**: This project was completed as part of Harvard's CS50. Requirements for this project can be found [here](https://cs50.harvard.edu/x/2020/tracks/web/finance/).   

**Description:** Website where users can create an account, buy, and sell imaginary stocks.   

For this project, I implemented the following functionality:

1. `register`: Allows a user to "register" on the site. The username and password are submitted via Flask and stored in a SQLite database
2. `quote`: Allows a user to look up the price of a stock using the symbol
3. `buy`: Allows a user to buy the imaginary stock; Purchased stocks are saved to the database and money balance is updated
4. `index`: Displays a summary table of the user's current funds and stocks
5. `sell`: Allows a user to sell stocks; Sold stocks are removed from the database and the money balance is updated
6. `history`: Displays a table showing the transaction history for the user

