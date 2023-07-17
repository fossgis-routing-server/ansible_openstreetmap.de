vagrant:
	./init_vagrant_inventory.sh
	ansible-playbook -l vagrant -i vagrant.ini -u vagrant site.yml

miller:
	ansible-playbook -l miller -i hosts.ini site.yml

ptolemy:
	ansible-playbook -l ptolemy -i hosts.ini site.yml

bonne:
	ansible-playbook -l bonne -i hosts.ini site.yml

robinson:
	ansible-playbook -l robinson -i hosts.ini site.yml

aitov:
	ansible-playbook -l aitov -i hosts.ini site.yml

lambert:
	ansible-playbook -l lambert -i hosts.ini site.yml

gall:
	ansible-playbook -l gall -i hosts.ini site.yml

bessel:
	ansible-playbook -l bessel -i hosts.ini site.yml

dev-overpass:
	ansible-playbook -l dev.overpass-api.de -i hosts.ini site.yml

dns-update:
	ansible-playbook -l dns -i hosts.ini -t dns site.yml

certs:
	ansible-playbook -l acme -i hosts.ini -t certificates site.yml

tile:
	ansible-playbook -l tile -i hosts.ini site.yml
