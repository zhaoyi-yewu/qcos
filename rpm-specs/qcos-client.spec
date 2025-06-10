%{!?upstream_version: %global upstream_version %{version}%{?milestone}}
%if 0%{?fedora} || 0%{?rhel} > 7
%global pyver %{python3_pkgversion}
%else
%global pyver 2
%endif

%if 0%{?rhel} || 0%{?fedora}
%global rdo 1
%endif

Name:          qcos
Version:       %{version}
Release:       1%{?milestone}%{?dist}
Summary:       QCOS command line interface
License:       MulanPSL-2.0
URL:           none
Source0:       qcos-%{version}.tar.gz
BuildArch:     noarch
BuildRequires: python3
Requires:      python3

%description
QCOS command line interface

%package -n python3-qcosclient
Summary:        Python QCOS client/shell
Group:          Applications/System
Requires:       python3-cliff >= 3.7.0
Requires:       python3-argcomplete >= 1.9.5

%description -n python3-qcosclient
QCOS command line interface

%prep
%autosetup  -p1 -n qcos-%{version}

%build
%py3_build

%install
%py3_install

%files -n python3-qcosclient
%license LICENSE
%{_bindir}/qcos-cli
%{python3_sitelib}/qcos/__init__.py
%{python3_sitelib}/qcos/client
%{python3_sitelib}/qcos/common
%{python3_sitelib}/qcos/libs
%{python3_sitelib}/qcos*.egg-info
%exclude %{python3_sitelib}/qcos/api_server.py
%exclude %{python3_sitelib}/qcos/server.py
%exclude %{python3_sitelib}/qcos/__pycache__

%changelog
* Mon Jun 9 2025 Yi Zhao <zhaoyi_yewu@cmss.chinamobile.com> 1.0.0
- Update to 1.0.0
