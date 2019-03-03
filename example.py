from libtado.api import Tado

t = Tado("my@email.com", "myPassword", "client_secret")

print(t.me)
print(t.home)
print(t.zones)
print(t.get_state(1))
