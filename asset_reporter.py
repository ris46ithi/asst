"""Generates reports from scans, and indicates.

  * Scan completion percentage.
  * New assets added, assets missing, and assets that have moved.
"""

from __future__ import print_function
import yaml
import os
import os.path
import csv
from datetime import datetime


def invert(d):
    """Returns an inversion of dictionary.

    Given { a: [b, c, d], e: [f, g, h] },
    returns { b: a, c: a, d: a, f: e, g: e, h: e}.
    """

    return dict((v, k) for k in d for v in d[k])


# http://stackoverflow.com/a/1630350
def lookahead(iterable):
    """Generator indicating the last element of iteration.

    The generator returns a tuple, (data, last). last is True if this
    is the last element of the iteration.
    """

    it = iter(iterable)
    last = it.next()  # next(it) in Python 3
    for val in it:
        yield last, False
        last = val
    yield last, True


class AssetReporterError(Exception):
    """Indicates an error in generating asset report."""
    pass


def read_scanned_tags(scan_fname):
    """Return list of scanned tags from a scan CSV file."""
    tag_ids = []
    with open(os.path.join("scans", scan_fname)) as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"',
                            doublequote=False, escapechar="\\")
        for i, row in enumerate(reader, start=1):
            try:
                tag_ids.append(row[0])
            except IndexError as exc:
                msg = "incorrect no. of columns in line no. {0} of file '{1}'"
                raise AssetReporterError(msg.format(i, scan_fname))

    return tag_ids


def get_tags_by_location(tag_ids):
    """Return a dictionary mapping location to tag IDs, from tag list.

    The tag list contains location tags and asset tags. All asset
    tags appearing after a location tag, belong to that
    location. Based on this the locations are mapped to assets in
    a dictionary, and the dictionary is returned.
    """
    tags_by_location = {}
    location = None

    for tag_id in tag_ids:
        if tag_id.startswith("LOCAT"):
            tags_by_location[tag_id] = []
            location = tag_id
        else:
            if location is None:
                msg = "Location not specified for asset {0}".format(tag_id)
                raise AssetReporterError(msg)
            tags_by_location[location].append(tag_id)

    return tags_by_location


def get_moved_assets(curr_assets_loc, prev_assets_loc):
    """Returns assets that were moved between two scans.

    The returned value is a list of tuples (asset, prev_loc,
    curr_loc). Each element corresponds to tag ID.
    """
    moved_assets = []
    for asset in curr_assets_loc:
        if asset in prev_assets_loc:
            curr_loc = curr_assets_loc[asset]
            prev_loc = prev_assets_loc[asset]

            if curr_loc != prev_loc:
                moved_assets.append((asset, prev_loc, curr_loc))

    return moved_assets


class AssetReporter(object):
    """Main report generation class."""

    def __init__(self):
        self.assets_db = yaml.load(open("assets.yml"))
        self.assets_by_date = {}

    def _get_asset_name(self, asset):
        """Returns the name of asset specified by tag ID."""
        try:
            return self.assets_db["assets"][asset]["type"]["name"]
        except:
            return "Unknown"

    def _is_defunct(self, asset):
        """Returns the name of asset specified by tag ID."""
        try:
            return self.assets_db["assets"][asset]["status"] == "Defunct"
        except:
            return False

    def _get_location_name(self, location_id):
        """Returns the name of the location specified by tag ID."""
        try:
            facility = self.assets_db["locations"][location_id]["facility"]
            location = self.assets_db["locations"][location_id]["name"]
            return "%s:%s" % (facility, location)
        except:
            return "Unknown"

    def read_scans(self):
        """Read all the scan files.

        Read the scan files present in the scans/ folder, and updates
        them in _assets_by_date attribute.
        """

        for scan_fname in os.listdir("scans"):
            if scan_fname.endswith("~") or scan_fname.startswith("."):
                continue
            scan_date, _ = os.path.splitext(scan_fname)
            try:
                scan_date = datetime.strptime(scan_date, "%Y-%m-%d")
            except ValueError:
                msg = "incorrect scan filename '{0}' should be YYYY-MM-DD.csv"
                raise AssetReporterError(msg.format(scan_fname))
            tag_ids = read_scanned_tags(scan_fname)
            tags_by_location = get_tags_by_location(tag_ids)
            self.assets_by_date[scan_date] = tags_by_location

    def _report_scan_progress(self, curr_assets):
        """Generate scan progress report for a scan date."""

        curr_locations = set(curr_assets.keys())
        all_locations = set(self.assets_db["locations"].keys())

        missed_locations = all_locations - curr_locations
        percentage = (len(curr_locations) * 100) / len(all_locations)

        # If the percentage is zero, we would like the progress bar to
        # show a small segment so that, the color is visible.
        if percentage == 0:
            percentage = 1

        percentage_to_color = ["red", "yellow", "lime", "lime"]
        if percentage > 100:
            percentage = 100
        color = percentage_to_color[int(percentage / 33.33)]

        print("*Progress*:\n")

        progress_bar = 'progress::{0}[color="{1}", caption="{2} / {3} Locations"]'
        print(progress_bar.format(percentage, color,
                                  len(curr_locations),
                                  len(all_locations)))

        if missed_locations:
            print("*Missed Locations*: ", end="")
        for location, last in lookahead(missed_locations):
            end = "" if last else ", "
            print("{0}".format(self._get_location_name(location)), end=end)
        print("\n")

    def _report_asset_changes(self, prev_assets, curr_assets):
        """Generate report for asset changes between two scans."""

        prev_assets_loc = invert(prev_assets)
        curr_assets_loc = invert(curr_assets)

        missed_assets = set(prev_assets_loc.keys()) - set(curr_assets_loc.keys())
        new_assets = set(curr_assets_loc.keys()) - set(prev_assets_loc.keys())

        print('[role="table table-striped"]')
        print("|======")

        for asset in new_assets:
            asset_name = self._get_asset_name(asset)
            location = curr_assets_loc[asset]
            location_name = self._get_location_name(location)
            action = "[green]#New Asset#"
            print("| {3} | {1} [`{0}`] | {2}".format(asset,
                                                     asset_name,
                                                     location_name,
                                                     action))
        for asset in missed_assets:
            if self._is_defunct(asset):
                continue
            asset_name = self._get_asset_name(asset)
            location = prev_assets_loc[asset]
            location_name = self._get_location_name(location)
            action = "[red]#Missing Asset#"
            print("| {3} | {1} [`{0}`] | {2}".format(asset,
                                                     asset_name,
                                                     location_name,
                                                     action))

        moved_assets = get_moved_assets(curr_assets_loc, prev_assets_loc)
        for asset, prev_loc, curr_loc in moved_assets:
            asset_name = self._get_asset_name(asset)
            prev_loc_name = self._get_location_name(prev_loc)
            curr_loc_name = self._get_location_name(curr_loc)
            action = "[olive]#Moved Asset#"
            print("| {4} | {1} [`{0}`] | {2} to {3}".format(asset,
                                                            asset_name,
                                                            prev_loc_name,
                                                            curr_loc_name,
                                                            action))

        print("|======")
        print("")

    def _report_assets_by_location(self, curr_assets):
        """Report for list of assets, based on location"""

        asset_type = "Asset Type#"
        count = "[green]#Count#"
        asset_id = "[green]#Asset ID's#"
        for location in curr_assets.keys():
            assets_name = {""}
            location_name = self._get_location_name(location)
            print("=== Location: {0}".format(location_name))
            #
            # To get the asset types in the specified location.
            #
            for asset in curr_assets[location]: 
                assets_name.add(self._get_asset_name(asset))

            assets_name.pop()

            print('['
                  'role="table table-striped",'
                  'options="header",'
                  'cols="40%,10%,50%asciidoc"'
                  ']')
            print("|======")
            print("| Asset Type | Count | Asset IDs")

            for assets_name in assets_name:
                asset_list = []
                for asset in curr_assets[location]:
                    asset_name = self._get_asset_name(asset)
                    if asset_name != assets_name:
                        continue
                    asset_list.append(asset)
                asset_list_as_str = "".join("    * `{0}`\n".format(x) for x in asset_list)
                print("| {0} | {1}\n|\n{2}".format(assets_name, len(asset_list),
                                                    asset_list_as_str))

            print("|======")

    def gen_report(self):
        """Generate report for information obtained from scans."""

        print("= Asset Report")
        print(":toc:")
        print("")
        curr_assets = None
        curr_date = None

        print("== Assets by Location")
        last_scan_date = max(self.assets_by_date.keys())
        last_assets = self.assets_by_date[last_scan_date]
        self._report_assets_by_location(last_assets)

        print("== Asset Changes")

        for scan_date in sorted(self.assets_by_date.keys()):
            prev_assets = curr_assets
            curr_assets = self.assets_by_date[scan_date]
            curr_date = scan_date

            if prev_assets is None:
                continue

            curr_date_str = curr_date.strftime("%d %b '%y")

            print("=== {0}".format(curr_date_str))
            self._report_scan_progress(curr_assets)
            self._report_asset_changes(prev_assets, curr_assets)


def main():
    """Main script entry point."""
    try:
        reporter = AssetReporter()
        reporter.read_scans()
        reporter.gen_report()
    except AssetReporterError as exc:
        print("asset_reporter: {0}".format(exc))


if __name__ == "__main__":
    main()
