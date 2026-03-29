class Ledger:
    def __init__(self):
        self.accounts = {}

    def create_account(self, account_id, opening_balance):
        self.accounts[account_id] = opening_balance

    def transfer(self, from_id, to_id, amount):
        self.accounts[from_id] -= amount
        self.accounts[to_id] += amount

    def balance(self, account_id):
        return self.accounts[account_id]
