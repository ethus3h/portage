# Copyright: 2005 Gentoo Foundation
# Author(s): Brian Harring (ferringb@gentoo.org)
# License: GPL2
# $Id$

import os, stat
import flat_hash
import cache_errors
from portage.ebuild import eclass_cache 
from template import reconstruct_eclasses, serialize_eclasses
from portage.util.mappings import ProtectedDict

# this is the old cache format, flat_list.  count maintained here.
magic_line_count = 22

# store the current key order *here*.
class database(flat_hash.database):
	complete_eclass_entries = False
	auxdbkey_order=('DEPEND', 'RDEPEND', 'SLOT', 'SRC_URI',
		'RESTRICT',  'HOMEPAGE',  'LICENSE', 'DESCRIPTION',
		'KEYWORDS',  'INHERITED', 'IUSE', 'CDEPEND',
		'PDEPEND',   'PROVIDE', 'EAPI')

	autocommits = True

	def __init__(self, *args, **config):
		super(database, self).__init__(*args, **config)
		self.location = os.path.join(self.location[:-len(self.label)], "metadata/cache")
		self.ec = eclass_cache.cache(self.location)

	def __getitem__(self, cpv):
		d = flat_hash.database.__getitem__(self, cpv)

		if "_eclasses_" not in d:
			if "INHERITED" in d:
				d["_eclasses_"] = self.ec.get_eclass_data(d["INHERITED"].split(), from_master_only=True)
				del d["INHERITED"]
		else:
			d["_eclasses_"] = reconstruct_eclasses(cpv, d["_eclasses_"])

		return d

	def _parse_data(self, data, mtime):
		# easy attempt first.
		data = list(data)
		if len(data) != magic_line_count:
			return flat_hash.database._parse_data(self, data, mtime)

		# this one's interesting.
		d = {}

		for line in data:
			# yes, meant to iterate over a string.
			hashed = False
			for idx, c in enumerate(line):
				if not c.isalpha():
					if c == "=" and idx > 0:
						hashed = True
						d[line[:idx]] = line[idx + 1:]
					elif c == "_" or c.isdigit():
						continue
					break
				elif not c.isupper():
					break
			
			if not hashed:
				# non hashed.
				d.clear()
				for idx, key in enumerate(self.auxdbkey_order):
					d[key] = data[idx].strip()
				break
		d["_mtime_"] = mtime
		return d


		
	def _setitem(self, cpv, values):
		values = ProtectedDict(values)
		
		# hack.  proper solution is to make this a __setitem__ override, since template.__setitem__ 
		# serializes _eclasses_, then we reconstruct it.
		if "_eclasses_" in values:
			values["INHERITED"] = ' '.join(reconstruct_eclasses(cpv, values["_eclasses_"]).keys())
			del values["_eclasses_"]

		flat_hash.database._setitem(self, cpv, values)
