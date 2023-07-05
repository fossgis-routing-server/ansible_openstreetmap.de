# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Apache webserver
  config.vm.network "forwarded_port", guest: 80, host: 8089
  config.vm.network "forwarded_port", guest: 443, host: 8443

  # Never sync the current directory to /vagrant.
  config.vm.synced_folder ".", "/vagrant", disabled: true

  config.vm.provider "libvirt" do |lv, override|
    lv.memory = 8196
    lv.nested = true
  end

  # Note: Makefile does not work yet.
  config.vm.define "bookworm", primary: true do |sub|
    sub.vm.box = "debian/bookworm64"
    sub.vm.provision :ansible do |s|
      s.playbook = "bootstrap.yml"
    end
  end
end
