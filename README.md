Salon & Spa Module for Marcos Organizador de Negocios
------

Marcos Organizador de Negocios is a collection of addons for OpenERP localized for Dominican Republic.
This is the Salon & Spa module.


Installation
------------

To configure a development enviroment (in Ubuntu):

0. Make sure you have the latest version of 'virtualenv', that includes
   the latest version of `setuptools` (> 0.7).

    **Important**: You'll need setuptools 0.7.x for it to pull dependencies from
    VCS repos. Follow the [installation instructions](https://pypi.python.org/pypi/setuptools/0.7.4#installation-instructions)
    for your system if you don't have it already.

1. Create a virtual enviroment (if you haven't already):

        $ mkvirtualenv openerp.marcos

2. Clone this repo to your marcos_addons dir:
   (Example: `~/.virtualenvs/src/marcos_addons`)

        $ git clone https://github.com/jventuravs/salon_spa.git

3. Clone the required custom dependencies into the same repo:

        $ git clone https://github.com/jventuravs/product_bundle.git
        $ git clone https://github.com/jventuravs/resource_planning.git
