vagrant-bookworm:
	./init_vagrant_inventory.sh bookworm
	ansible-playbook -l vagrant -i vagrant.ini -u vagrant site.yml

vagrant: vagrant-bookworm

miller:
	ansible-playbook -l miller -i hosts.ini site.yml

conic:
	ansible-playbook -l conic -i hosts.ini site.yml

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
	ansible-playbook -l dns -i hosts.ini dns.yml

certs:
	ansible-playbook -l acme -i hosts.ini -t certificates site.yml

tile:
	ansible-playbook -l tile -i hosts.ini site.yml

dev:
	ansible-playbook -l dev -i hosts.ini site.yml

monitor:
	ansible-galaxy install -r requirements.yml -f
	ansible-playbook -l icinga2agent -i hosts.ini monitoring.yml
