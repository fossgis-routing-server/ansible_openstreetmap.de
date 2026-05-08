# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  if Vagrant.has_plugin?("vagrant-env") then
    config.env.enable
  end
  memory = ENV["VAGRANT_MEMORY"] || 2048

  # Never sync the current directory to /vagrant.
  config.vm.synced_folder ".", "/vagrant", disabled: true

  config.vm.provider "libvirt" do |lv, override|
    lv.memory = memory
    lv.nested = true
  end

  config.vm.define "trixie", autostart: false do |sub|
    sub.vm.box = "debian/trixie64"
    sub.vm.network "forwarded_port", guest: 80, host: 8089
    sub.vm.network "forwarded_port", guest: 443, host: 8443
    # Virtualbox fallback for hosts without libvirt. The libvirt block at
    # the top of the file sets memory + nested for libvirt; this mirrors
    # the memory side for virtualbox.
    sub.vm.provider "virtualbox" do |v|
      v.memory = memory
    end
    sub.vm.provision :ansible do |s|
      s.playbook = "bootstrap.yml"
    end
  end

  # Two-VM setup for the valhalla role. Both VMs share a libvirt
  # private_network so they can SSH each other (graph push, deploy
  # trigger) using the same IPs the ansible controller uses to reach
  # them. Use VAGRANT_VALHALLA_MEMORY (default 6144).
  valhalla_memory = ENV["VAGRANT_VALHALLA_MEMORY"] || 6144
  valhalla_cpus   = ENV["VAGRANT_VALHALLA_CPUS"]   || 4

  {
    "valhalla-service" => "192.168.123.10",
    "valhalla-builder" => "192.168.123.11",
  }.each do |name, ip|
    config.vm.define name, autostart: false do |sub|
      sub.vm.box = "debian/trixie64"
      sub.vm.hostname = name
      sub.vm.network "private_network", ip: ip
      sub.vm.provider "libvirt" do |lv|
        lv.memory = valhalla_memory
        lv.cpus   = valhalla_cpus
      end
      sub.vm.provider "virtualbox" do |v|
        v.memory = valhalla_memory
        v.cpus   = valhalla_cpus
      end
      sub.vm.provision :ansible do |s|
        s.playbook = "bootstrap.yml"
      end
    end
  end
end
