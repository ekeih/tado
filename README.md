# Tado python library

A library to control your Tado Smart Thermostat. This repository contains an actual library in `libtado/api.py` and a proof of concept command line client in `libtado/__main__.py`.

**The tested version of APIs is Tado v2.**

## Installation

You can download official library with `pip install libtado`.

But because I do not own a Tado anymore you may want to use a fork of libtado instead. For example you can install the fork that is currently (February 2019) maintained and improved by @germainlefebvre4. Please note that I do not monitor or verify changes of this repository. Please check the source yourself.

```sh
git clone https://github.com/germainlefebvre4/libtado.git
```

Please check out https://libtado.readthedocs.io for more documentation.

## Preparation

Retrieve your `CLIENT_SECRET` before running the script otherwise you will get a `401 Unauthorized Access`.

To get your `CLIENT_SECRET` enable the Developper Mode when logging in and catch the Headers. You will find the form data like this :
```
client_id: tado-web-app
client_secret: fndskjnjzkefjNFRNkfKJRNFKRENkjnrek
grant_type: password
password: MyBeautifulPassword
scope: home.user
username: email@example.com
```

Then you just have to get the value in the attribute `client_secret`. You will need it to connect to your account through Tado APIs. The `client_secret` never dies so you can base your script on it.

*Your `CLIENT_SECRET` must be kept secret.*

## Usage

Download the repository. You can work inside it. Beware that the examples assume that they can access the file `./libtado/api.py`.

Now you can call it in your Pyhton script!

```python
from libtado import api

t = api.Tado('my@email.com', 'myPassword', 'client_secret')

print(t.me)
print(t.home)
print(t.zones)
print(t.get_state(1))
```

## Examples

An example script is provided in the repository as `example.py`.
It shows you how to use the library and expose some structured responses. A more detailed example is available in `libtado/__main__.py`.
