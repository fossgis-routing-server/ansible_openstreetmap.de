vm-bookworm:
	ansible-playbook -l bookworm -i ansible-vm.ini site.yml

vm-trixie:
	ansible-playbook -l trixie -i ansible-vm.ini site.yml

miller:
	ansible-playbook -l miller -i hosts.ini site.yml

conic:
	ansible-playbook -l conic -i hosts.ini site.yml

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

# Both hosts together — required for initial deploys due to SSH key sharing
valhalla:
	ansible-playbook -l valhalla_service,valhalla_builder -i hosts.ini site.yml

valhalla_service:
	ansible-playbook -l valhalla_service -i hosts.ini site.yml

valhalla_builder:
	ansible-playbook -l valhalla_builder -i hosts.ini site.yml

# Vagrant testing target for the valhalla role. Spins both VMs through the
# inventory init script first and then runs site.yml against both groups.
vagrant-valhalla:
	./init_vagrant_inventory.sh valhalla-service valhalla-builder
	ansible-playbook -l valhalla_service,valhalla_builder -i vagrant.ini site.yml

monitor:
	ansible-galaxy install -r requirements.yml -f
	ansible-playbook -l icinga2agent -i hosts.ini monitoring.yml
