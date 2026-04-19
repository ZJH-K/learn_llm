class Fib:
    def __init__(self):
        self.a = 0
        self.b = 1
    
    def __iter__(self):
        return self
    
    def __next__(self):
       value = self.a
       self.a, self.b = self.b, self.a + self.b
       return value
    
def fib_gen():
    a = 0
    b = 1
    while True:
        yield a
        a, b = b, a + b
        
if __name__ == "__main__":
    fib = Fib()
    for i, x in enumerate(fib):
        if i >= 10:
            break
        print(x)

    gen = fib_gen()
    for i in range(10):
        print(next(gen))