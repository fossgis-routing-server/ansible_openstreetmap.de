# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  if Vagrant.has_plugin?("vagrant-env") then
    config.env.enable
  end
  memory = ENV["VAGRANT_MEMORY"] || 2048

  # Apache webserver
  config.vm.network "forwarded_port", guest: 80, host: 8089
  config.vm.network "forwarded_port", guest: 443, host: 8443

  # Never sync the current directory to /vagrant.
  config.vm.synced_folder ".", "/vagrant", disabled: true

  config.vm.provider "libvirt" do |lv, override|
    lv.memory = memory
    lv.nested = true
  end

  config.vm.define "bookworm" do |sub|
    sub.vm.box = "debian/bookworm64"
    sub.vm.provision :ansible do |s|
      s.playbook = "bootstrap.yml"
    end
  end
end
